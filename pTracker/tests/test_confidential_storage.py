import io
import os
import shutil
import tempfile
import uuid
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from pTracker.common.confidential_storage import CompanyFileStorage
from pTracker.common.confidential_storage import FileTooLarge
from pTracker.common.confidential_storage import InvalidStorageKey
from pTracker.common.confidential_storage import StorageError
from pTracker.common.confidential_storage import StoredFileMissing
from pTracker.common.upload_validation import DOCUMENT_TYPES
from pTracker.common.upload_validation import IMAGE_TYPES
from pTracker.common.upload_validation import UploadRejected
from pTracker.common.upload_validation import clean_filename
from pTracker.common.upload_validation import validate_upload


def png_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(buffer, format='PNG')
    return buffer.getvalue()


def docx_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('word/document.xml', '<w:document/>')
    return buffer.getvalue()


class CompanyFileStorageTests(SimpleTestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.storage = CompanyFileStorage(self.root)
        self.company = uuid.uuid4()
        self.other_company = uuid.uuid4()

    def test_save_writes_under_company_uuid_and_category(self):
        stored = self.storage.save(self.company, 'documents', [b'hello ', b'world'], 'txt', 100)
        self.assertRegex(stored.storage_key, r'^documents/[0-9a-f]{32}\.txt$')
        self.assertEqual(stored.size, 11)
        path = os.path.join(self.root, str(self.company), stored.storage_key)
        with open(path, 'rb') as handle:
            self.assertEqual(handle.read(), b'hello world')
        self.assertEqual(os.stat(path).st_mode & 0o777 & ~0o640, 0)
        self.assertEqual(self.storage.read(self.company, stored.storage_key), b'hello world')
        # No temporary file left behind
        self.assertEqual(os.listdir(os.path.dirname(path)), [os.path.basename(path)])

    def test_each_save_gets_a_new_name(self):
        first = self.storage.save(self.company, 'documents', [b'a'], 'txt', 10)
        second = self.storage.save(self.company, 'documents', [b'b'], 'txt', 10)
        self.assertNotEqual(first.storage_key, second.storage_key)
        self.assertEqual(self.storage.read(self.company, first.storage_key), b'a')

    def test_too_large_is_rejected_and_nothing_is_kept(self):
        with self.assertRaises(FileTooLarge):
            self.storage.save(self.company, 'documents', [b'x' * 6, b'x' * 6], 'txt', 10)
        self.assertEqual(os.listdir(os.path.join(self.root, str(self.company), 'documents')), [])

    def test_interrupted_write_leaves_no_file(self):
        def chunks():
            yield b'part'
            raise RuntimeError('worker interrupted')
        with self.assertRaises(RuntimeError):
            self.storage.save(self.company, 'documents', chunks(), 'txt', 100)
        self.assertEqual(os.listdir(os.path.join(self.root, str(self.company), 'documents')), [])

    def test_traversal_and_malformed_keys_are_rejected(self):
        for key in ('../x.txt', 'documents/../../etc/passwd', '/etc/passwd',
                    f'documents/{"a" * 32}.txt/../..', 'secrets/' + 'a' * 32 + '.txt',
                    'documents/' + 'A' * 32 + '.txt', 'documents\\' + 'a' * 32 + '.txt', '', None):
            with self.subTest(key=key), self.assertRaises(InvalidStorageKey):
                self.storage.open(self.company, key)

    def test_invalid_company_identifier_is_rejected(self):
        for company in ('../other', 'Digital Mesh', '', None, '4'):
            with self.subTest(company=company), self.assertRaises(InvalidStorageKey):
                self.storage.save(company, 'documents', [b'x'], 'txt', 10)

    def test_invalid_category_and_extension_are_rejected(self):
        with self.assertRaises(InvalidStorageKey):
            self.storage.save(self.company, '../profile', [b'x'], 'txt', 10)
        with self.assertRaises(InvalidStorageKey):
            self.storage.save(self.company, 'documents', [b'x'], 'php/../x', 10)

    def test_key_from_another_company_is_not_found(self):
        stored = self.storage.save(self.other_company, 'documents', [b'theirs'], 'txt', 100)
        with self.assertRaises(StoredFileMissing):
            self.storage.open(self.company, stored.storage_key)

    def test_symlinked_company_directory_is_refused(self):
        stored = self.storage.save(self.other_company, 'documents', [b'theirs'], 'txt', 100)
        os.symlink(os.path.join(self.root, str(self.other_company)), os.path.join(self.root, str(self.company)))
        with self.assertRaises(StorageError):
            self.storage.open(self.company, stored.storage_key)
        with self.assertRaises(StorageError):
            self.storage.save(self.company, 'documents', [b'x'], 'txt', 10)

    def test_symlinked_file_is_refused(self):
        outside = os.path.join(self.root, 'outside.txt')
        with open(outside, 'w') as handle:
            handle.write('secret')
        directory = os.path.join(self.root, str(self.company), 'documents')
        os.makedirs(directory)
        key = 'documents/' + 'b' * 32 + '.txt'
        os.symlink(outside, os.path.join(self.root, str(self.company), key))
        with self.assertRaises(StorageError):
            self.storage.open(self.company, key)

    def test_missing_file_and_missing_root(self):
        with self.assertRaises(StoredFileMissing):
            self.storage.open(self.company, 'documents/' + 'c' * 32 + '.txt')
        with self.assertRaises(StorageError):
            CompanyFileStorage(os.path.join(self.root, 'nope')).save(self.company, 'documents', [b'x'], 'txt', 10)

    def test_delete_and_list_keys(self):
        stored = self.storage.save(self.company, 'other', [b'x'], 'txt', 10)
        self.assertEqual(self.storage.list_keys(self.company), {stored.storage_key})
        self.assertTrue(self.storage.delete(self.company, stored.storage_key))
        self.assertFalse(self.storage.delete(self.company, stored.storage_key))
        self.assertEqual(self.storage.list_keys(self.company), set())

    def test_remove_stale_partials_only_touches_own_company(self):
        self.storage.save(self.company, 'documents', [b'x'], 'txt', 10)
        self.storage.save(self.other_company, 'documents', [b'x'], 'txt', 10)
        own = os.path.join(self.root, str(self.company), 'documents', '.abc.part')
        theirs = os.path.join(self.root, str(self.other_company), 'documents', '.abc.part')
        for path in (own, theirs):
            open(path, 'w').close()
            os.utime(path, (0, 0))
        self.assertEqual(self.storage.remove_stale_partials(self.company, 60), 1)
        self.assertFalse(os.path.exists(own))
        self.assertTrue(os.path.exists(theirs))


class UploadValidationTests(SimpleTestCase):

    def test_detects_types_from_content(self):
        cases = [
            ('logo.png', png_bytes(), 'image/png'),
            ('report.pdf', b'%PDF-1.7\n%...', 'application/pdf'),
            ('notes.txt', 'Grüße'.encode(), 'text/plain'),
            ('data.csv', b'a,b\n1,2\n', 'text/csv'),
            ('offer.docx', docx_bytes(), DOCUMENT_TYPES[1].content_type),
        ]
        for name, content, expected in cases:
            with self.subTest(name=name):
                upload = SimpleUploadedFile(name, content, content_type='application/x-anything')
                self.assertEqual(validate_upload(upload, DOCUMENT_TYPES, 10_000).content_type, expected)

    def test_client_content_type_is_ignored(self):
        upload = SimpleUploadedFile('evil.pdf', b'<html><script>alert(1)</script>', content_type='application/pdf')
        with self.assertRaises(UploadRejected):
            validate_upload(upload, DOCUMENT_TYPES, 10_000)

    def test_extension_must_match_content(self):
        upload = SimpleUploadedFile('invoice.pdf', png_bytes(), content_type='application/pdf')
        with self.assertRaises(UploadRejected):
            validate_upload(upload, DOCUMENT_TYPES, 10_000)

    def test_disallowed_types_are_rejected(self):
        for name, content in (('x.svg', b'<svg xmlns="http://www.w3.org/2000/svg"/>'),
                              ('x.exe', b'MZ\x90\x00\x03\x00\x00\x00'),
                              ('x.zip', b'PK\x03\x04' + b'\x00' * 30)):
            with self.subTest(name=name), self.assertRaises(UploadRejected):
                validate_upload(SimpleUploadedFile(name, content), DOCUMENT_TYPES, 10_000)

    def test_logo_accepts_images_only(self):
        with self.assertRaises(UploadRejected):
            validate_upload(SimpleUploadedFile('logo.pdf', b'%PDF-1.7'), IMAGE_TYPES, 10_000)
        self.assertEqual(validate_upload(SimpleUploadedFile('logo.png', png_bytes()), IMAGE_TYPES, 10_000).extension,
                         'png')

    def test_damaged_image_is_rejected(self):
        with self.assertRaises(UploadRejected):
            validate_upload(SimpleUploadedFile('logo.png', png_bytes()[:30]), IMAGE_TYPES, 10_000)

    def test_empty_and_oversized_are_rejected(self):
        with self.assertRaises(UploadRejected):
            validate_upload(SimpleUploadedFile('a.txt', b''), DOCUMENT_TYPES, 10)
        with self.assertRaises(UploadRejected):
            validate_upload(SimpleUploadedFile('a.txt', b'x' * 11), DOCUMENT_TYPES, 10)
        with self.assertRaises(UploadRejected):
            validate_upload(None, DOCUMENT_TYPES, 10)

    def test_clean_filename(self):
        self.assertEqual(clean_filename('../../etc/passwd', 'txt'), 'passwd')
        self.assertEqual(clean_filename('C:\\Users\\me\\offer.pdf', 'pdf'), 'offer.pdf')
        self.assertEqual(clean_filename('a\x00b\r\n"c.pdf', 'pdf'), 'ab"c.pdf')
        self.assertEqual(clean_filename('..', 'pdf'), 'file.pdf')
        self.assertEqual(len(clean_filename('x' * 400 + '.pdf', 'pdf')), 255)
        self.assertTrue(clean_filename('x' * 400 + '.pdf', 'pdf').endswith('.pdf'))
