""" Content-based validation of uploaded files.

The type is decided from the file's own bytes (signature plus a structural
check), never from the client's Content-Type, and the extension of the
uploaded name must agree with it. The stored extension and the Content-Type
served later both come from the detected type. SVG/HTML and other active
content is deliberately not accepted.
"""

import io
import os
import unicodedata
import zipfile

from PIL import Image

SNIFF_BYTES = 8192


class UploadRejected(Exception):
    """ The message is safe to return to the client. """


class FileType:

    def __init__(self, extension, content_type, accepted_extensions, is_image=False):
        self.extension = extension
        self.content_type = content_type
        self.accepted_extensions = accepted_extensions
        self.is_image = is_image


PNG = FileType('png', 'image/png', ('png',), is_image=True)
JPEG = FileType('jpg', 'image/jpeg', ('jpg', 'jpeg'), is_image=True)
WEBP = FileType('webp', 'image/webp', ('webp',), is_image=True)
PDF = FileType('pdf', 'application/pdf', ('pdf',))
DOCX = FileType('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', ('docx',))
XLSX = FileType('xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', ('xlsx',))
TXT = FileType('txt', 'text/plain', ('txt',))
CSV = FileType('csv', 'text/csv', ('csv',))

IMAGE_TYPES = (PNG, JPEG, WEBP)
DOCUMENT_TYPES = (PDF, DOCX, XLSX, TXT, CSV) + IMAGE_TYPES


def clean_filename(name, fallback_extension):
    """ Display-only copy of the client's filename: last path component, no
    control/format characters, at most 255 characters. Never used as a path. """
    name = unicodedata.normalize('NFC', str(name or ''))
    name = name.replace('\\', '/').split('/')[-1]
    name = ''.join(ch for ch in name if unicodedata.category(ch)[0] != 'C').strip().strip('.')
    if not name:
        return f'file.{fallback_extension}'
    if len(name) > 255:
        stem, ext = os.path.splitext(name)
        name = stem[:255 - len(ext)] + ext if len(ext) < 20 else name[:255]
    return name


def _extension(name):
    return os.path.splitext(str(name or ''))[1].lower().lstrip('.')


def _detect(upload, head):
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return PNG
    if head.startswith(b'\xff\xd8\xff'):
        return JPEG
    if len(head) >= 12 and head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return WEBP
    if head.startswith(b'%PDF-'):
        return PDF
    if head.startswith(b'PK\x03\x04'):
        return _detect_office(upload)
    if b'\x00' not in head:
        try:
            head.decode('utf-8')
        except UnicodeDecodeError as error:
            # A multi-byte character cut off at the end of the sniffed block is fine.
            if error.start < len(head) - 4:
                return None
        return TXT
    return None


def _detect_office(upload):
    """ OOXML documents are zip archives; only the member names are read. """
    try:
        upload.seek(0)
        with zipfile.ZipFile(upload) as archive:
            names = set(archive.namelist())
    except (zipfile.BadZipFile, OSError, ValueError):
        return None
    if '[Content_Types].xml' not in names:
        return None
    if 'word/document.xml' in names:
        return DOCX
    if 'xl/workbook.xml' in names:
        return XLSX
    return None


def _verify_image(upload):
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            image.verify()
    except Exception:
        # Pillow raises many types (incl. DecompressionBombError) for bad input.
        raise UploadRejected('The image file is damaged or not a supported image') from None


def validate_upload(upload, allowed_types, max_bytes):
    """ Returns the detected FileType or raises UploadRejected. Leaves the
    upload rewound to the start. """
    if upload is None:
        raise UploadRejected('A file is required')
    if not upload.size:
        raise UploadRejected('The file is empty')
    if upload.size > max_bytes:
        raise UploadRejected(f'The file is larger than {max_bytes // (1024 * 1024)} MB')

    upload.seek(0)
    head = upload.read(SNIFF_BYTES)
    file_type = _detect(upload, head)
    extension = _extension(upload.name)
    if file_type is TXT and extension == 'csv':
        file_type = CSV

    allowed_names = ', '.join(sorted({t.extension for t in allowed_types}))
    if file_type is None or file_type not in allowed_types:
        raise UploadRejected(f'File type not allowed. Allowed types: {allowed_names}')
    if extension not in file_type.accepted_extensions:
        raise UploadRejected('The file extension does not match the file content')
    if file_type.is_image:
        _verify_image(upload)

    upload.seek(0)
    return file_type


def validate_content(content, allowed_types, max_bytes):
    """ validate_upload for raw bytes with no trustworthy file name (e.g. a
    base64 image sent in JSON): the type comes from the content alone.
    Returns the detected FileType or raises UploadRejected. """
    if not content:
        raise UploadRejected('The file is empty')
    if len(content) > max_bytes:
        raise UploadRejected(f'The file is larger than {max_bytes // (1024 * 1024)} MB')
    buffer = io.BytesIO(content)
    file_type = _detect(buffer, content[:SNIFF_BYTES])
    if file_type is None or file_type not in allowed_types:
        allowed_names = ', '.join(sorted({t.extension for t in allowed_types}))
        raise UploadRejected(f'File type not allowed. Allowed types: {allowed_names}')
    if file_type.is_image:
        _verify_image(buffer)
    return file_type
