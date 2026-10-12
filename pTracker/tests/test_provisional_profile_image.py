""" Pending profile photos: upload (v1 save-employee-profile-image), viewing,
approval and rejection, stored per company under the confidential root.

user_profile_provisional / auth_user profile tables are unmanaged legacy tables
that do not exist in the SQLite test database, so UserDA, the capability check
and company membership are replaced by in-memory fakes; the companies, the
storage service, the file system layout and the transactions are real. """

import io
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponseBase
from django.test import TestCase
from django.test import override_settings
from PIL import Image

from pTracker.api.user.user_management_bl import UserManagementBL
from pTracker.api.user.user_management_bl_v1 import UserManagementBL_V1
from pTracker.common.company_context import ActiveCompany
from pTracker.common.company_context import clear_active_company
from pTracker.common.company_context import set_active_company
from pTracker.common.confidential_storage import CompanyFileStorage
from pTracker.dataaccess.platform_access.document_models import CompanyDocument
from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Tenant

PROVISIONAL_DIR = 'profile_image_provisional'
VALUE_REGEX = r'^{uuid}/profile_image_provisional/[0-9a-f]{{32}}\.{ext}$'
LIVE_REGEX = r'^{uuid}/employee_profile_photo/[0-9a-f]{{32}}\.{ext}$'


def image_bytes(fmt='PNG', size=(8, 8)):
    buffer = io.BytesIO()
    Image.new('RGB', size, 'green').save(buffer, format=fmt)
    return buffer.getvalue()


class FakeUserDA():
    """ Just the UserDA calls the profile image flows make. """

    def __init__(self):
        self.users = {}
        self.photos = {}
        self.rows = []
        self.fail_on_create = False

    def get_user_by_id(self, user_id):
        return self.users.get(int(user_id))

    def get_pending_profile_field_change(self, emp_id, field, status=1):
        return [r for r in self.rows if r.emp_id == emp_id and r.field == field and r.status == status]

    get_employee_profile_change_by_emp_id_and_status_and_field = get_pending_profile_field_change

    def get_employee_profile_change_by_emp_id_and_status(self, emp_id, status=1):
        return [r for r in self.rows if r.emp_id == emp_id and r.status == status]

    def delete_user_profile_provisional_entries(self, emp_id, field, status=1):
        self.rows = [r for r in self.rows if not (r.emp_id == emp_id and r.field == field and r.status == status)]

    def create_user_profile_provisional_object(self, user_id, emp_id, field, value):
        return SimpleNamespace(emp_id=emp_id, field=field, value=value, status=1, created_by=user_id)

    def create_emp_profile_changes(self, rows):
        if self.fail_on_create:
            raise RuntimeError('database unavailable')
        self.rows.extend(rows)

    def get_user_profile_by_id(self, emp_id):
        return SimpleNamespace(profile_photo=self.photos.get(emp_id))

    def update_user_profile(self, emp_id, data):
        self.photos[emp_id] = data['profile_photo']

    def update_auth_user(self, data, emp_id):
        pass

    def update_emergency_contact(self, data, emp_id):
        pass


class FakeOrgDA():
    members = {}

    def is_company_member(self, company_id, user_id):
        return int(user_id) in self.members.get(company_id, set())

    def get_member_ids(self, company_id):
        return self.members.get(company_id, set())


class ProvisionalProfileImageTests(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.media = tempfile.mkdtemp() + '/'
        self.addCleanup(shutil.rmtree, self.root, True)
        self.addCleanup(shutil.rmtree, self.media, True)
        overrides = override_settings(COMPANY_DOCUMENT_STORAGE_ROOT=self.root, MEDIA_ROOT=self.media)
        overrides.enable()
        self.addCleanup(overrides.disable)
        self.addCleanup(clear_active_company)

        tenant = Tenant.objects.create(slug='t', name='Tenant')
        self.company_a = Company.objects.create(tenant=tenant, legal_name='A Ltd', short_name='A')
        self.company_b = Company.objects.create(tenant=tenant, legal_name='B Ltd', short_name='B')

        # 10, 11: employees of A; 12: HR of A (manage + approve); 20: employee of B; 21: HR of B.
        self.user_da = FakeUserDA()
        for user_id in (10, 11, 12, 20, 21):
            self.user_da.users[user_id] = SimpleNamespace(id=user_id, username=f'E{user_id}')
        FakeOrgDA.members = {self.company_a.id: {10, 11, 12}, self.company_b.id: {20, 21}}
        self.capabilities = {12: {'employee.manage', 'employee.approve_profile_changes'},
                             21: {'employee.manage', 'employee.approve_profile_changes'}}

        def has_capability(user_id, code, company_id=None):
            return code in self.capabilities.get(user_id, set())

        for module in ('pTracker.api.user.user_management_bl', 'pTracker.api.user.user_management_bl_v1'):
            for name, value in (('UserDA', lambda: self.user_da), ('OrgDA', FakeOrgDA),
                                ('has_capability', has_capability), ('Logs', mock.MagicMock())):
                patcher = mock.patch(f'{module}.{name}', value)
                patcher.start()
                self.addCleanup(patcher.stop)
        patcher = mock.patch('pTracker.api.user.profile_image_biz.Logs', mock.MagicMock())
        patcher.start()
        self.addCleanup(patcher.stop)

    # Helpers

    def act_as(self, user_id, company):
        set_active_company(ActiveCompany(user_id, company.id, company.short_name))

    def upload(self, user_id, company, emp_id, name='me.png', content=None, content_type='image/png'):
        self.act_as(user_id, company)
        image = SimpleUploadedFile(name, content if content is not None else image_bytes(), content_type)
        request = SimpleNamespace(data={'emp_id': str(emp_id)}, FILES={'image': image})
        with self.captureOnCommitCallbacks(execute=True):
            return UserManagementBL_V1().save_employee_profile_image(user_id, request)

    def view(self, user_id, company, emp_id):
        self.act_as(user_id, company)
        return UserManagementBL().get_pending_profile_image_content(user_id, emp_id)

    def act_on(self, user_id, company, emp_id, action):
        self.act_as(user_id, company)
        with self.captureOnCommitCallbacks(execute=True):
            return UserManagementBL().apply_action_on_profile_changes(
                user_id, {'emp_id': emp_id, 'action': action, 'field': 'emp_image'})

    def pending_value(self, emp_id):
        rows = self.user_da.get_pending_profile_field_change(emp_id, 'emp_image')
        return rows[0].value if rows else None

    def stored_path(self, value):
        return os.path.join(self.root, value)

    def provisional_files(self, company):
        directory = os.path.join(self.root, str(company.uuid), PROVISIONAL_DIR)
        return sorted(os.listdir(directory)) if os.path.isdir(directory) else []

    # Upload

    def test_upload_is_stored_under_company_uuid(self):
        content = image_bytes()
        result = self.upload(10, self.company_a, 10, content=content)
        self.assertEqual(result, {'message': 'Profile image uploaded successfully'})

        value = self.pending_value(10)
        self.assertRegex(value, VALUE_REGEX.format(uuid=self.company_a.uuid, ext='png'))
        self.assertFalse(os.path.isabs(value))
        with open(self.stored_path(value), 'rb') as handle:
            self.assertEqual(handle.read(), content)
        # Nothing written to the old public-ish location or the document table.
        self.assertFalse(os.path.exists(os.path.join(self.media, 'confidential_docs')))
        self.assertEqual(CompanyDocument.objects.count(), 0)

    def test_two_companies_use_separate_directories(self):
        self.upload(10, self.company_a, 10)
        self.upload(20, self.company_b, 20, name='b.jpg', content=image_bytes('JPEG'), content_type='image/jpeg')
        self.assertRegex(self.pending_value(10), VALUE_REGEX.format(uuid=self.company_a.uuid, ext='png'))
        self.assertRegex(self.pending_value(20), VALUE_REGEX.format(uuid=self.company_b.uuid, ext='jpg'))
        self.assertEqual(len(self.provisional_files(self.company_a)), 1)
        self.assertEqual(len(self.provisional_files(self.company_b)), 1)

    def test_replacing_removes_previous_file_after_commit(self):
        self.upload(10, self.company_a, 10)
        first = self.pending_value(10)
        self.upload(10, self.company_a, 10)
        second = self.pending_value(10)
        self.assertNotEqual(first, second)
        self.assertFalse(os.path.exists(self.stored_path(first)))
        self.assertTrue(os.path.exists(self.stored_path(second)))
        self.assertEqual(len(self.user_da.rows), 1)

    def test_failed_database_write_keeps_previous_and_removes_new_file(self):
        self.upload(10, self.company_a, 10)
        first = self.pending_value(10)
        self.user_da.fail_on_create = True
        result = self.upload(10, self.company_a, 10)
        self.assertEqual(result['status'], 499)
        self.assertTrue(os.path.exists(self.stored_path(first)))
        self.assertEqual([os.path.basename(first)], self.provisional_files(self.company_a))

    def test_manager_cannot_upload_for_another_company_employee(self):
        result = self.upload(12, self.company_a, 20)
        self.assertEqual(result['status'], 403)
        self.assertEqual(self.provisional_files(self.company_a), [])
        self.assertEqual(self.provisional_files(self.company_b), [])

    def test_employee_cannot_upload_for_colleague(self):
        self.assertEqual(self.upload(10, self.company_a, 11)['status'], 403)
        self.assertIsNone(self.pending_value(11))

    def test_invalid_and_oversized_files_are_rejected(self):
        cases = [
            ('me.gif', image_bytes('GIF'), 'image/png'),
            ('me.png', image_bytes('JPEG'), 'image/png'),
            ('me.png', b'<svg onload=alert(1)>', 'image/png'),
            ('me.png', b'\x89PNG\r\n\x1a\n' + b'0' * (2 * 1024 * 1024), 'image/png'),
        ]
        for name, content, content_type in cases:
            with self.subTest(name=name, size=len(content)):
                result = self.upload(10, self.company_a, 10, name=name, content=content, content_type=content_type)
                self.assertEqual(result['status'], 499)
        self.assertEqual(self.provisional_files(self.company_a), [])
        self.assertIsNone(self.pending_value(10))

    def test_malicious_filename_is_not_used_on_disk(self):
        self.upload(10, self.company_a, 10, name='../../../../etc/cron.d/x.png')
        value = self.pending_value(10)
        self.assertRegex(value, VALUE_REGEX.format(uuid=self.company_a.uuid, ext='png'))
        self.assertTrue(os.path.realpath(self.stored_path(value)).startswith(os.path.realpath(self.root)))

    def test_upload_without_active_company_is_refused(self):
        clear_active_company()
        request = SimpleNamespace(data={'emp_id': '10'}, FILES={'image': SimpleUploadedFile('me.png', image_bytes())})
        result = UserManagementBL_V1().save_employee_profile_image(10, request)
        self.assertEqual(result['status'], 403)
        self.assertEqual(os.listdir(self.root), [])

    def test_storage_root_missing_is_reported(self):
        shutil.rmtree(self.root)
        result = self.upload(10, self.company_a, 10)
        self.assertEqual(result['status'], 503)
        self.assertNotIn(self.root, str(result))
        self.assertIsNone(self.pending_value(10))

    # Viewing

    def test_owner_and_approver_can_view(self):
        content = image_bytes()
        self.upload(10, self.company_a, 10, content=content)
        for user_id in (10, 12):
            with self.subTest(user=user_id):
                response = self.view(user_id, self.company_a, 10)
                self.assertIsInstance(response, HttpResponseBase)
                self.assertEqual(response.content, content)
                self.assertEqual(response['Content-Type'], 'image/png')
                self.assertEqual(response['Cache-Control'], 'private, no-store')
                self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_others_cannot_view(self):
        self.upload(10, self.company_a, 10)
        self.assertEqual(self.view(11, self.company_a, 10)['status'], 403)  # colleague
        self.assertEqual(self.view(21, self.company_b, 10)['status'], 403)  # HR of another company

    def test_file_of_another_company_is_never_served(self):
        # Employee 10 also belongs to B, but the photo was uploaded under A.
        self.upload(10, self.company_a, 10)
        FakeOrgDA.members[self.company_b.id].add(10)
        self.assertEqual(self.view(21, self.company_b, 10)['status'], 404)
        self.assertEqual(self.view(10, self.company_b, 10)['status'], 404)

    def test_missing_pending_image_and_missing_file(self):
        self.assertEqual(self.view(10, self.company_a, 10)['status'], 404)
        self.upload(10, self.company_a, 10)
        os.unlink(self.stored_path(self.pending_value(10)))
        self.assertEqual(self.view(10, self.company_a, 10)['status'], 404)

    def test_waiting_action_returns_endpoint_url_not_a_path(self):
        self.upload(10, self.company_a, 10)
        self.act_as(12, self.company_a)
        result = UserManagementBL().get_employee_profile_info_waiting_action(12, 10)
        self.assertTrue(result['emp_image'].endswith('/pending-profile-image/10/'), result['emp_image'])
        self.assertNotIn(str(self.company_a.uuid), str(result))
        self.assertNotIn(self.root, str(result))

    # Approve / reject

    def test_approval_publishes_photo_and_removes_pending_file(self):
        content = image_bytes()
        self.upload(10, self.company_a, 10, content=content)
        value = self.pending_value(10)
        self.user_da.photos[10] = 'E10.jpeg'
        old_live = os.path.join(self.media, 'employee_profile_photo', 'E10.jpeg')
        os.makedirs(os.path.dirname(old_live))
        open(old_live, 'wb').close()

        result = self.act_on(12, self.company_a, 10, 'APPROVED')
        self.assertEqual(result, {'message': 'Changes applied'})
        live = self.user_da.photos[10]
        self.assertRegex(live, LIVE_REGEX.format(uuid=self.company_a.uuid, ext='png'))
        with open(self.stored_path(live), 'rb') as handle:
            self.assertEqual(handle.read(), content)
        self.assertFalse(os.path.exists(old_live))
        self.assertFalse(os.path.exists(self.stored_path(value)))
        self.assertIsNone(self.pending_value(10))

    def test_approver_of_another_company_cannot_approve(self):
        self.upload(10, self.company_a, 10)
        self.assertEqual(self.act_on(21, self.company_b, 10, 'APPROVED')['status'], 403)
        self.assertIsNotNone(self.pending_value(10))

    def test_reject_removes_pending_file(self):
        self.upload(10, self.company_a, 10)
        value = self.pending_value(10)
        self.assertEqual(self.act_on(12, self.company_a, 10, 'REJECTED'), {'message': 'Changes applied'})
        self.assertFalse(os.path.exists(self.stored_path(value)))
        self.assertIsNone(self.pending_value(10))

    # Rows written before this change ("<username>.<ext>" under MEDIA_ROOT)

    def legacy_pending(self, emp_id, name, content):
        directory = os.path.join(self.media, 'confidential_docs', PROVISIONAL_DIR)
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, name), 'wb') as handle:
            handle.write(content)
        self.user_da.rows.append(SimpleNamespace(emp_id=emp_id, field='emp_image', value=name, status=1))
        return os.path.join(directory, name)

    def test_legacy_pending_image_can_be_viewed_and_approved(self):
        content = image_bytes('JPEG')
        legacy_path = self.legacy_pending(10, 'E10.jpeg', content)
        response = self.view(12, self.company_a, 10)
        self.assertEqual(response.content, content)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

        self.assertEqual(self.act_on(12, self.company_a, 10, 'APPROVED'), {'message': 'Changes applied'})
        live = self.user_da.photos[10]
        self.assertRegex(live, LIVE_REGEX.format(uuid=self.company_a.uuid, ext='jpg'))
        with open(self.stored_path(live), 'rb') as handle:
            self.assertEqual(handle.read(), content)
        self.assertFalse(os.path.exists(legacy_path))

    def test_legacy_value_cannot_traverse(self):
        outside = os.path.join(self.media, 'secret.png')
        with open(outside, 'wb') as handle:
            handle.write(image_bytes())
        self.user_da.rows.append(SimpleNamespace(emp_id=10, field='emp_image', value='../../secret.png', status=1))
        self.assertEqual(self.view(10, self.company_a, 10)['status'], 404)

    def test_new_upload_replaces_legacy_pending_image(self):
        legacy_path = self.legacy_pending(10, 'E10.png', image_bytes())
        self.upload(10, self.company_a, 10)
        self.assertRegex(self.pending_value(10), VALUE_REGEX.format(uuid=self.company_a.uuid, ext='png'))
        self.assertFalse(os.path.exists(legacy_path))

    # Document cleanup must not treat pending photos as orphans

    def test_document_listing_ignores_pending_photos(self):
        self.upload(10, self.company_a, 10)
        self.assertEqual(CompanyFileStorage(self.root).list_keys(self.company_a.uuid), set())
