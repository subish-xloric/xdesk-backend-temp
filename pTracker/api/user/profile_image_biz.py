""" Employee profile photos: pending (not yet approved) photos, and the
signed-link endpoint for live photos (storage: pTracker/common/profile_photo.py).

New uploads are kept in the company's confidential storage
(pTracker/common/confidential_storage.py):

    <COMPANY_DOCUMENT_STORAGE_ROOT>/<company uuid>/profile_image_provisional/<32 hex>.<ext>

and user_profile_provisional.value holds the path relative to the storage root,
"<company uuid>/profile_image_provisional/<32 hex>.<ext>" - never an absolute
path. The company in the value is the company the photo was uploaded under;
it is only ever read back for that same (verified, active) company.

Rows written before this change hold a bare file name ("<username>.<ext>") under
MEDIA_ROOT/confidential_docs/profile_image_provisional/. They keep working
(read, approve, replace) from that old location; nothing is moved.

This class does no authorization: callers check the caller may act on the
employee and pass the caller's active company.
"""

import re
import time

from django.conf import settings
from django.http import HttpResponse

from pTracker.common.confidential_storage import CompanyFileStorage
from pTracker.common.confidential_storage import PROVISIONAL_PROFILE_IMAGE
from pTracker.common.confidential_storage import StorageError
from pTracker.common.confidential_storage import StoredFileMissing
from pTracker.common.file_manager import FileManager
from pTracker.common.logs import Logs
from pTracker.common.profile_photo import ProfilePhotoStore
from pTracker.common.profile_photo import read_photo_token
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.platform_access.tenancy_da import TenancyDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA

VALUE_PATTERN = re.compile(
    r'^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/'
    r'(' + PROVISIONAL_PROFILE_IMAGE + r'/[0-9a-f]{32}\.(jpg|jpeg|png))$')
LEGACY_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,200}\.(jpg|jpeg|png)$')
CONTENT_TYPES = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'}
URL_CACHE_SECONDS = 600


class ProvisionalProfileImageBL():

    def __init__(self):
        self.__logs = Logs()
        self.__storage = CompanyFileStorage()
        self.__file_manager = FileManager()

    @staticmethod
    def is_company_stored(value):
        """ True for a value written by save(), False for a legacy file name. """
        return bool(VALUE_PATTERN.match(value or ''))

    def save(self, company, image, extension, max_bytes):
        """ Writes the (already validated) upload under the company's directory
        and returns the value to store in user_profile_provisional. """
        stored = self.__storage.save(company.uuid, PROVISIONAL_PROFILE_IMAGE, image.chunks(), extension, max_bytes)
        return f'{company.uuid}/{stored.storage_key}'

    def read(self, value, company_uuid):
        """ (bytes, content type) of a pending photo. Raises StoredFileMissing if
        there is none, or it belongs to another company, and StorageError if
        storage is unavailable. """
        parsed = VALUE_PATTERN.match(value or '')
        if parsed:
            stored_company, storage_key, extension = parsed.groups()
            if stored_company != str(company_uuid):
                raise StoredFileMissing('Pending image belongs to another company')
            return self.__storage.read(stored_company, storage_key), CONTENT_TYPES[extension]

        legacy = LEGACY_NAME_PATTERN.match(value or '')
        if not legacy:
            raise StoredFileMissing('No pending image')
        content = self.__file_manager.read_file(self.__legacy_path(value))
        if not content:
            raise StoredFileMissing('Pending image file is missing')
        return content, CONTENT_TYPES[legacy.group(1).lower()]

    def delete(self, value):
        """ Removes a pending photo's file; never raises. """
        parsed = VALUE_PATTERN.match(value or '')
        if parsed:
            try:
                self.__storage.delete(parsed.group(1), parsed.group(2))
            except StorageError as error:
                self.__logs.error(f'Pending profile image delete failed: {error}')
        elif LEGACY_NAME_PATTERN.match(value or ''):
            self.__file_manager.delete_file(self.__legacy_path(value))

    @staticmethod
    def __legacy_path(name):
        return f'{settings.MEDIA_ROOT}confidential_docs/profile_image_provisional/{name}'


class ProfilePhotoBL():
    """ GET profile-photo/<emp_id>/?t=<token>: no login; the signed token
    (pTracker/common/profile_photo.py) is the authorization. It names the
    company the link was issued for, and the photo is served only from that
    company: a photo stored per company must be stored under it, an older
    photo only if the employee is an active member of it. """

    def __init__(self):
        self.__logs = Logs()

    def get_content(self, emp_id, token):
        # Same answer for a bad or expired token, an employee outside the
        # company, no photo and a missing file: nothing can be probed.
        not_found = {"error": "Not found", "status": 404}
        signed = read_photo_token(emp_id, token)
        if signed is None:
            return not_found
        company_uuid, expires = signed
        profile = UserDA().get_user_profile_by_id(emp_id)
        value = profile.profile_photo if profile else None
        photos = ProfilePhotoStore()
        if value and not photos.is_company_stored(value):
            company = TenancyDA().get_company_by_uuid(company_uuid)
            if company is None or not OrgDA().is_company_member(company.id, emp_id):
                return not_found
        try:
            content, content_type = photos.read(value, company_uuid)
        except StoredFileMissing:
            return not_found
        except StorageError as error:
            self.__logs.error(f'Profile photo read failed: emp={emp_id}: {error}')
            return {"error": "Image storage is temporarily unavailable", "status": 503}

        response = HttpResponse(content, content_type=content_type)
        response['X-Content-Type-Options'] = 'nosniff'
        max_age = max(0, min(int(expires - time.time()), URL_CACHE_SECONDS))
        response['Cache-Control'] = f'private, max-age={max_age}'
        response['Content-Security-Policy'] = "default-src 'none'; sandbox"
        return response
