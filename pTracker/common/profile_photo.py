""" Employees' approved (live) profile photos.

Storage: the employee's company confidential storage
(pTracker/common/confidential_storage.py):

    <COMPANY_DOCUMENT_STORAGE_ROOT>/<company uuid>/employee_profile_photo/<32 hex>.<ext>

user_profile.profile_photo holds the path relative to the storage root,
"<company uuid>/employee_profile_photo/<32 hex>.<ext>". Rows written before
this change hold a bare file name under MEDIA_ROOT/employee_profile_photo/;
they are still read from there until `manage.py migrate_profile_photos` moves
them.

Access: photos are not served from a public directory. API responses that
the caller is authorized to receive carry a signed link,
GET .../profile-photo/<emp_id>/?t=<token>, so it works in a plain <img>/<Image>
tag without the JWT. The token is bound to the employee and to the company the
link was issued for (the request's active company), and expires after
PROFILE_PHOTO_URL_MAX_AGE seconds, rounded up to a URL_BUCKET_SECONDS window so
repeated responses reuse the same URL and image caches work. ProfilePhotoBL
serves a photo only from that company (see read_photo_token).
"""

import base64
import binascii
import math
import re
import time
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.urls import reverse

from pTracker.common.company_context import get_active_company
from pTracker.common.company_context import get_request_memo
from pTracker.common.confidential_storage import CompanyFileStorage
from pTracker.common.confidential_storage import EMPLOYEE_PROFILE_PHOTO
from pTracker.common.confidential_storage import StorageError
from pTracker.common.confidential_storage import StoredFileMissing
from pTracker.common.file_manager import FileManager
from pTracker.common.logs import Logs
from pTracker.common.upload_validation import JPEG
from pTracker.common.upload_validation import PNG
from pTracker.common.upload_validation import UploadRejected
from pTracker.common.upload_validation import validate_content
from pTracker.common.upload_validation import validate_upload
from pTracker.dataaccess.platform_access.tenancy_da import TenancyDA

MAX_BYTES = 2 * 1024 * 1024
ALLOWED_TYPES = (JPEG, PNG)
VALUE_PATTERN = re.compile(
    r'^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/'
    r'(' + EMPLOYEE_PROFILE_PHOTO + r'/[0-9a-f]{32}\.(jpg|jpeg|png))$')
LEGACY_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,200}\.(jpg|jpeg|png)$', re.IGNORECASE)
CONTENT_TYPES = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'}
DATA_URL_PREFIX = re.compile(r'^data:image/[a-zA-Z0-9.+-]+;base64,')
URL_SALT = 'pTracker.employee-profile-photo'
URL_BUCKET_SECONDS = 600


def profile_photo_url(emp_id, profile_photo):
    """ Signed absolute link to the employee's photo, or "" when there is no
    photo or no company to scope the link to. """
    if not profile_photo or emp_id is None:
        return ""
    company_uuid = _issuing_company_uuid(profile_photo)
    if not company_uuid:
        return ""
    expires = math.ceil((time.time() + settings.PROFILE_PHOTO_URL_MAX_AGE) / URL_BUCKET_SECONDS) * URL_BUCKET_SECONDS
    token = signing.Signer(salt=URL_SALT).sign(f'{int(emp_id)}:{company_uuid}:{expires}')
    path = reverse('profile_photo', kwargs={'emp_id': int(emp_id)})
    return f"{settings.API_PUBLIC_URL.rstrip('/')}{path}?{urlencode({'t': token})}"


def read_photo_token(emp_id, token):
    """ (company uuid, expiry epoch) the link was issued for, or None when the
    token is forged, expired or for another employee. """
    try:
        payload = signing.Signer(salt=URL_SALT).unsign(token or '')
    except signing.BadSignature:
        return None
    parts = payload.split(':')
    if len(parts) != 3 or parts[0] != str(emp_id) or not parts[2].isdigit():
        return None
    if int(parts[2]) < time.time():
        return None
    return parts[1], int(parts[2])


def _issuing_company_uuid(profile_photo):
    """ The request's active company; outside a request (no company context)
    only a photo stored per company can be linked, to its own company. """
    active = get_active_company()
    if active is None:
        parsed = VALUE_PATTERN.match(profile_photo or '')
        return parsed.group(1) if parsed else None
    memo = get_request_memo()
    key = ('company_uuid', active.company_id)
    if memo is not None and key in memo:
        return memo[key]
    company = TenancyDA().get_company_by_id(active.company_id)
    company_uuid = str(company.uuid) if company else None
    if memo is not None:
        memo[key] = company_uuid
    return company_uuid


class ProfilePhotoStore():

    def __init__(self):
        self.__logs = Logs()
        self.__storage = CompanyFileStorage()
        self.__file_manager = FileManager()

    @staticmethod
    def is_company_stored(value):
        return bool(VALUE_PATTERN.match(value or ''))

    def save_upload(self, company, upload):
        """ Validates an uploaded file (content, extension, 2 MB) and stores it.
        Returns the value for user_profile.profile_photo; raises UploadRejected
        or StorageError. """
        file_type = validate_upload(upload, ALLOWED_TYPES, MAX_BYTES)
        return self.__save(company, upload.chunks(), file_type.extension, MAX_BYTES)

    def save_bytes(self, company, content, max_bytes=MAX_BYTES):
        """ max_bytes is only raised for migrating photos that already exist. """
        file_type = validate_content(content, ALLOWED_TYPES, max_bytes)
        return self.__save(company, [content], file_type.extension, max_bytes)

    def save_base64(self, company, data):
        """ Accepts plain base64 or a "data:image/...;base64," URL. """
        if isinstance(data, bytes):
            data = data.decode('ascii', errors='replace')
        encoded = DATA_URL_PREFIX.sub('', str(data or '').strip(), count=1)
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise UploadRejected('The profile photo is not valid base64') from None
        return self.save_bytes(company, content)

    def read(self, value, company_uuid=None):
        """ (bytes, content type); raises StoredFileMissing / StorageError.
        With company_uuid, a photo stored under another company is missing. """
        parsed = VALUE_PATTERN.match(value or '')
        if parsed:
            stored_company, storage_key, extension = parsed.groups()
            if company_uuid is not None and stored_company != str(company_uuid):
                raise StoredFileMissing('Profile photo belongs to another company')
            company_uuid = stored_company
            return self.__storage.read(company_uuid, storage_key), CONTENT_TYPES[extension]
        legacy = LEGACY_NAME_PATTERN.match(value or '')
        if not legacy:
            raise StoredFileMissing('No profile photo')
        content = self.__file_manager.read_file(self.legacy_path(value))
        if not content:
            raise StoredFileMissing('Profile photo file is missing')
        return content, CONTENT_TYPES[legacy.group(1).lower()]

    def read_or_none(self, value):
        try:
            return self.read(value)[0]
        except StorageError:
            return None

    def delete(self, value):
        """ Removes a photo's file; never raises. """
        parsed = VALUE_PATTERN.match(value or '')
        if parsed:
            try:
                self.__storage.delete(parsed.group(1), parsed.group(2))
            except StorageError as error:
                self.__logs.error(f'Profile photo delete failed: {error}')
        elif LEGACY_NAME_PATTERN.match(value or ''):
            self.__file_manager.delete_file(self.legacy_path(value))

    @staticmethod
    def legacy_path(name):
        return f'{settings.MEDIA_ROOT}employee_profile_photo/{name}'

    def __save(self, company, chunks, extension, max_bytes):
        stored = self.__storage.save(company.uuid, EMPLOYEE_PROFILE_PHOTO, chunks, extension, max_bytes)
        return f'{company.uuid}/{stored.storage_key}'
