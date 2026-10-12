""" Filesystem storage for company confidential files.

Layout: <COMPANY_DOCUMENT_STORAGE_ROOT>/<company uuid>/<category>/<32 hex>.<ext>

Categories: profile/documents/other hold platform_company_document files;
profile_image_provisional and employee_profile_photo hold employees' pending
and approved profile photos, which are tracked by user_profile_provisional and
user_profile.profile_photo instead (see pTracker/common/profile_photo.py).

Callers only ever handle the relative storage key "<category>/<32 hex>.<ext>";
the absolute path is built here and never returned. Every path is rebuilt from
a parsed UUID and a key that must match KEY_PATTERN, so client input (company
names, filenames, "../") can never reach the filesystem. On top of that, each
directory level is opened without following symlinks and the final path must
resolve inside the company directory, so a planted symlink cannot redirect a
read or write to another company or outside the root.

This service does no authorization: callers resolve the company from the
caller's verified membership first (see CompanyDocumentBL).
"""

import errno
import hashlib
import os
import re
import stat
import time
import uuid

from django.conf import settings

DOCUMENT_CATEGORIES = ('profile', 'documents', 'other')
PROVISIONAL_PROFILE_IMAGE = 'profile_image_provisional'
EMPLOYEE_PROFILE_PHOTO = 'employee_profile_photo'
CATEGORIES = DOCUMENT_CATEGORIES + (PROVISIONAL_PROFILE_IMAGE, EMPLOYEE_PROFILE_PHOTO)
KEY_PATTERN = re.compile(
    r'^(profile|documents|other|profile_image_provisional|employee_profile_photo)/([0-9a-f]{32})\.([a-z0-9]{1,8})$')
PARTIAL_SUFFIX = '.part'
DIR_MODE = 0o750
FILE_MODE = 0o640


class StorageError(Exception):
    """ Storage unavailable or a path failed a safety check. The message is safe
    to log: it never contains an absolute path or file contents. """


class InvalidStorageKey(StorageError):
    pass


class StoredFileMissing(StorageError):
    pass


class FileTooLarge(StorageError):
    pass


class StoredFile:

    def __init__(self, storage_key, size, sha256):
        self.storage_key = storage_key
        self.size = size
        self.sha256 = sha256


class CompanyFileStorage():

    def __init__(self, root=None):
        self.__root = root or settings.COMPANY_DOCUMENT_STORAGE_ROOT

    # Public API

    def save(self, company_uuid, category, chunks, extension, max_bytes):
        """ Writes chunks to a new, server-named file and returns a StoredFile.
        The data goes to a temporary file first and is linked into place only
        once complete, so readers never see a half-written file and an existing
        file is never overwritten. """
        if category not in CATEGORIES:
            raise InvalidStorageKey('Unknown storage category')
        if not re.fullmatch(r'[a-z0-9]{1,8}', extension or ''):
            raise InvalidStorageKey('Invalid file extension')

        directory = self.__directory(company_uuid, category, create=True)
        name = f'{uuid.uuid4().hex}.{extension}'
        partial = os.path.join(directory, f'.{uuid.uuid4().hex}{PARTIAL_SUFFIX}')
        final = os.path.join(directory, name)

        digest = hashlib.sha256()
        size = 0
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
        try:
            fd = os.open(partial, flags, FILE_MODE)
            with os.fdopen(fd, 'wb') as handle:
                for chunk in chunks:
                    size += len(chunk)
                    if size > max_bytes:
                        raise FileTooLarge('File is larger than the allowed size')
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            self.__link_into_place(partial, final)
        except OSError as error:
            raise StorageError(f'Could not write file ({errno.errorcode.get(error.errno, error.errno)})') from None
        finally:
            self.__remove_quietly(partial)

        return StoredFile(f'{category}/{name}', size, digest.hexdigest())

    def open(self, company_uuid, storage_key):
        """ Binary file object for reading; the caller must close it (Django's
        FileResponse does). """
        path = self.__resolve(company_uuid, storage_key)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0))
        except FileNotFoundError:
            raise StoredFileMissing('Stored file is missing') from None
        except OSError as error:
            raise StorageError(f'Could not open file ({errno.errorcode.get(error.errno, error.errno)})') from None
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise StorageError('Stored path is not a regular file')
        return os.fdopen(fd, 'rb')

    def read(self, company_uuid, storage_key):
        with self.open(company_uuid, storage_key) as handle:
            return handle.read()

    def delete(self, company_uuid, storage_key):
        """ True if removed, False if it was already gone. """
        path = self.__resolve(company_uuid, storage_key)
        try:
            os.unlink(path)
            return True
        except FileNotFoundError:
            return False
        except OSError as error:
            raise StorageError(f'Could not delete file ({errno.errorcode.get(error.errno, error.errno)})') from None

    def list_keys(self, company_uuid, categories=DOCUMENT_CATEGORIES):
        """ Storage keys of the finished files in one company's directory
        (document categories unless told otherwise). """
        keys = set()
        for category in categories:
            try:
                directory = self.__directory(company_uuid, category, create=False)
            except StoredFileMissing:
                continue
            for entry in os.scandir(directory):
                key = f'{category}/{entry.name}'
                if KEY_PATTERN.match(key) and entry.is_file(follow_symlinks=False):
                    keys.add(key)
        return keys

    def remove_stale_partials(self, company_uuid, older_than_seconds=3600):
        """ Removes temporary files left by interrupted uploads in this company's
        directory only. Returns how many were removed. """
        removed = 0
        cutoff = time.time() - older_than_seconds
        for category in CATEGORIES:
            try:
                directory = self.__directory(company_uuid, category, create=False)
            except StoredFileMissing:
                continue
            for entry in os.scandir(directory):
                if (entry.name.startswith('.') and entry.name.endswith(PARTIAL_SUFFIX)
                        and entry.is_file(follow_symlinks=False)
                        and entry.stat(follow_symlinks=False).st_mtime < cutoff):
                    self.__remove_quietly(entry.path)
                    removed += 1
        return removed

    # Path handling

    def __root_path(self):
        root = os.path.realpath(self.__root)
        if not os.path.isdir(root):
            raise StorageError('Confidential storage root is not available')
        return root

    def __directory(self, company_uuid, category, create):
        if category not in CATEGORIES:
            raise InvalidStorageKey('Unknown storage category')
        root = self.__root_path()
        company_dir = self.__child_directory(root, self.__company_dir_name(company_uuid), create)
        return self.__child_directory(company_dir, category, create)

    def __child_directory(self, parent, name, create):
        """ parent/name as a real directory - never a symlink - created if asked. """
        path = os.path.join(parent, name)
        if create:
            try:
                os.mkdir(path, DIR_MODE)
            except FileExistsError:
                pass
            except OSError as error:
                raise StorageError(
                    f'Could not create directory ({errno.errorcode.get(error.errno, error.errno)})') from None
        try:
            mode = os.lstat(path).st_mode
        except FileNotFoundError:
            raise StoredFileMissing('Storage directory is missing') from None
        if not stat.S_ISDIR(mode):
            # Covers symlinks too: lstat does not follow them.
            raise StorageError('Storage directory is not a plain directory')
        return path

    def __resolve(self, company_uuid, storage_key):
        match = KEY_PATTERN.match(storage_key or '')
        if not match:
            raise InvalidStorageKey('Invalid storage key')
        category, stem, extension = match.groups()
        directory = self.__directory(company_uuid, category, create=False)
        path = os.path.join(directory, f'{stem}.{extension}')
        company_dir = os.path.dirname(directory)
        if os.path.commonpath([os.path.realpath(path), company_dir]) != company_dir:
            raise StorageError('Resolved path is outside the company directory')
        return path

    @staticmethod
    def __company_dir_name(company_uuid):
        try:
            return str(uuid.UUID(str(company_uuid)))
        except (TypeError, ValueError, AttributeError):
            raise InvalidStorageKey('Invalid company identifier') from None

    @staticmethod
    def __link_into_place(partial, final):
        try:
            os.link(partial, final)  # fails with EEXIST instead of overwriting
        except OSError as error:
            if error.errno not in (errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV):
                raise
            # Filesystem without hard links: the target name is a fresh random
            # UUID, so the existence check only guards against the impossible.
            if os.path.lexists(final):
                raise FileExistsError(errno.EEXIST, 'Target exists') from None
            os.rename(partial, final)

    @staticmethod
    def __remove_quietly(path):
        try:
            os.unlink(path)
        except OSError:
            pass
