""" Live profile photos: company storage, signed company-scoped links and the
login-free profile-photo endpoint, plus the writers that store photos (v1
direct upload, base64 profile edits, onboarding). UserDA is faked (unmanaged
legacy tables); users, companies, memberships, storage, signing, URL routing
and middleware are real. """

import base64
import os
import shutil
import tempfile
import time
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from rest_framework.test import APIClient

from pTracker.api.onboarding.onboarding_biz import OnboardingBL
from pTracker.api.user.user_management_bl_v1 import UserManagementBL_V1
from pTracker.api.user.user_management_helper_bl import UserManagementHelperBL
from pTracker.common.company_context import ActiveCompany
from pTracker.common.company_context import clear_active_company
from pTracker.common.company_context import set_active_company
from pTracker.common.profile_photo import ProfilePhotoStore
from pTracker.common.profile_photo import profile_photo_url
from pTracker.common.profile_photo import read_photo_token
from pTracker.common.upload_validation import UploadRejected
from pTracker.dataaccess.platform_access.membership_models import Membership
from pTracker.dataaccess.platform_access.role_models import Role
from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Tenant
from pTracker.tests.test_provisional_profile_image import FakeOrgDA
from pTracker.tests.test_provisional_profile_image import FakeUserDA
from pTracker.tests.test_provisional_profile_image import image_bytes

LIVE_REGEX = r'^{uuid}/employee_profile_photo/[0-9a-f]{{32}}\.{ext}$'


class ProfilePhotoTests(TestCase):

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

        self.user_da = FakeUserDA()
        for user_id in (10, 12, 20):
            self.user_da.users[user_id] = SimpleNamespace(id=user_id, username=f'E{user_id}')
        FakeOrgDA.members = {self.company_a.id: {10, 12}, self.company_b.id: {20}}
        self.capabilities = {12: {'employee.manage'}}

        def has_capability(user_id, code, company_id=None):
            return code in self.capabilities.get(user_id, set())

        patches = [('pTracker.api.user.user_management_bl_v1.UserDA', lambda: self.user_da),
                   ('pTracker.api.user.user_management_bl_v1.OrgDA', FakeOrgDA),
                   ('pTracker.api.user.user_management_bl_v1.has_capability', has_capability),
                   ('pTracker.api.user.profile_image_biz.UserDA', lambda: self.user_da)]
        for target, value in patches:
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    # Helpers

    def store_photo(self, emp_id, company, content=None):
        value = ProfilePhotoStore().save_bytes(company, content or image_bytes())
        self.user_da.photos[emp_id] = value
        return value

    def direct_upload(self, user_id, emp_id, name='new.png', content=None):
        set_active_company(ActiveCompany(user_id, self.company_a.id, 'A'))
        image = SimpleUploadedFile(name, content if content is not None else image_bytes(), 'image/png')
        with self.captureOnCommitCallbacks(execute=True):
            return UserManagementBL_V1().save_employee_profile_image(
                user_id, SimpleNamespace(data={'emp_id': str(emp_id)}, FILES={'image': image}))

    # Direct upload by employee.manage (v1 save-employee-profile-image)

    def test_manager_upload_goes_to_company_storage_and_replaces_old(self):
        old = self.store_photo(10, self.company_a)
        content = image_bytes()
        self.assertEqual(self.direct_upload(12, 10, content=content),
                         {'message': 'Profile image uploaded successfully'})
        new = self.user_da.photos[10]
        self.assertRegex(new, LIVE_REGEX.format(uuid=self.company_a.uuid, ext='png'))
        with open(os.path.join(self.root, new), 'rb') as handle:
            self.assertEqual(handle.read(), content)
        self.assertFalse(os.path.exists(os.path.join(self.root, old)))
        self.assertFalse(os.path.exists(os.path.join(self.media, 'employee_profile_photo')))

    def test_manager_upload_failure_keeps_old_photo(self):
        old = self.store_photo(10, self.company_a)
        with mock.patch.object(self.user_da, 'update_user_profile', side_effect=RuntimeError('db down')):
            result = self.direct_upload(12, 10)
        self.assertEqual(result['status'], 499)
        self.assertEqual(self.user_da.photos[10], old)
        directory = os.path.join(self.root, str(self.company_a.uuid), 'employee_profile_photo')
        self.assertEqual(os.listdir(directory), [os.path.basename(old)])

    def test_manager_cannot_upload_for_other_company_employee(self):
        self.assertEqual(self.direct_upload(12, 20)['status'], 403)
        self.assertNotIn(20, self.user_da.photos)

    # Base64 writers (create/update user, profile edit, onboarding)

    def test_base64_and_data_url_are_validated(self):
        store = ProfilePhotoStore()
        png = image_bytes()
        for data in (base64.b64encode(png).decode(), 'data:image/png;base64,' + base64.b64encode(png).decode()):
            value = store.save_base64(self.company_a, data)
            self.assertRegex(value, LIVE_REGEX.format(uuid=self.company_a.uuid, ext='png'))
        for bad in ('not base64!!', base64.b64encode(b'<svg onload=alert(1)>').decode(),
                    base64.b64encode(b'\xff\xd8\xff' + b'0' * (2 * 1024 * 1024)).decode()):
            with self.subTest(bad=bad[:20]):
                with self.assertRaises(UploadRejected):
                    store.save_base64(self.company_a, bad)

    def test_profile_edit_photo_uses_active_company(self):
        set_active_company(ActiveCompany(12, self.company_b.id, 'B'))
        value = UserManagementHelperBL().save_emp_profile_image('E20', {'photo': base64.b64encode(image_bytes())})
        self.assertRegex(value, LIVE_REGEX.format(uuid=self.company_b.uuid, ext='png'))
        clear_active_company()
        with self.assertRaises(UploadRejected):
            UserManagementHelperBL().save_emp_profile_image('E20', {'photo': base64.b64encode(image_bytes())})

    @mock.patch('pTracker.api.onboarding.onboarding_biz.Logs')
    def test_onboarding_photo_goes_to_organization_company_and_bad_photo_is_skipped(self, _logs):
        onboarding = OnboardingBL()
        value = onboarding.save_emp_profile_image(self.company_b.id, [{'photo': base64.b64encode(image_bytes('JPEG'))}])
        self.assertRegex(value, LIVE_REGEX.format(uuid=self.company_b.uuid, ext='jpg'))
        self.assertIsNone(onboarding.save_emp_profile_image(self.company_b.id, [{'photo': 'garbage'}]))
        self.assertIsNone(onboarding.save_emp_profile_image(self.company_b.id, [{}]))
        self.assertIsNone(onboarding.save_emp_profile_image(999, [{'photo': base64.b64encode(image_bytes())}]))




@override_settings(API_PUBLIC_URL='https://api.example.test', PROFILE_PHOTO_URL_MAX_AGE=900)
class ProfilePhotoEndpointTests(TestCase):
    """ Signed links and GET /v1/api/.../profile-photo/<emp_id>/?t=... with no
    login, through the real URL routing and middleware. """

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
        self.alice = self.member('alice', self.company_a)
        self.adam = self.member('adam', self.company_a)
        self.bob = self.member('bob', self.company_b)

        self.user_da = FakeUserDA()
        patcher = mock.patch('pTracker.api.user.profile_image_biz.UserDA', lambda: self.user_da)
        patcher.start()
        self.addCleanup(patcher.stop)

    def member(self, username, *companies):
        user = get_user_model().objects.create_user(username, password='x')
        for company in companies:
            Membership.objects.create(user=user, company=company,
                                      role=Role.objects.create(company=company, name=f'{username}-{company.id}'))
        return user

    def store_photo(self, user, company, content=None):
        value = ProfilePhotoStore().save_bytes(company, content or image_bytes())
        self.user_da.photos[user.id] = value
        return value

    def link(self, emp, viewer, company):
        """ The link an API response to viewer, acting in company, would carry. """
        set_active_company(ActiveCompany(viewer.id, company.id, company.short_name))
        try:
            return profile_photo_url(emp.id, self.user_da.photos.get(emp.id))
        finally:
            clear_active_company()

    def fetch(self, url):
        parts = urlsplit(url)
        return APIClient().get(f'{parts.path}?{parts.query}')

    # Links

    def test_link_is_absolute_signed_and_scoped_to_issuing_company(self):
        self.store_photo(self.alice, self.company_a)
        url = self.link(self.alice, self.adam, self.company_a)
        self.assertTrue(url.startswith('https://api.example.test/v1/api/'), url)
        self.assertIn(f'/profile-photo/{self.alice.id}/?t=', url)
        token = parse_qs(urlsplit(url).query)['t'][0]
        company_uuid, expires = read_photo_token(self.alice.id, token)
        self.assertEqual(company_uuid, str(self.company_a.uuid))
        self.assertTrue(900 <= expires - time.time() <= 1500)
        self.assertIsNone(read_photo_token(self.adam.id, token))
        self.assertNotIn(self.root, url)

    def test_no_link_without_photo(self):
        self.assertEqual(profile_photo_url(self.alice.id, ''), '')
        self.assertEqual(profile_photo_url(self.alice.id, None), '')

    def test_link_is_reused_within_window(self):
        self.store_photo(self.alice, self.company_a)
        self.assertEqual(self.link(self.alice, self.adam, self.company_a),
                         self.link(self.alice, self.adam, self.company_a))

    def test_link_outside_request_uses_photo_company_or_none(self):
        self.store_photo(self.alice, self.company_a)
        url = profile_photo_url(self.alice.id, self.user_da.photos[self.alice.id])
        token = parse_qs(urlsplit(url).query)['t'][0]
        self.assertEqual(read_photo_token(self.alice.id, token)[0], str(self.company_a.uuid))
        self.assertEqual(profile_photo_url(self.alice.id, 'alice.jpeg'), '')

    # Endpoint

    def test_signed_link_serves_photo_without_login(self):
        content = image_bytes()
        self.store_photo(self.alice, self.company_a, content)
        response = self.fetch(self.link(self.alice, self.adam, self.company_a))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        max_age = int(response['Cache-Control'].split('max-age=')[1])
        self.assertTrue(0 < max_age <= 600)

    def test_missing_forged_or_other_employee_token_is_404(self):
        self.store_photo(self.alice, self.company_a)
        self.store_photo(self.adam, self.company_a)
        alice_url = self.link(self.alice, self.adam, self.company_a)
        path = urlsplit(alice_url).path
        adam_query = urlsplit(self.link(self.adam, self.alice, self.company_a)).query
        client = APIClient()
        self.assertEqual(client.get(path).status_code, 404)
        self.assertEqual(client.get(f'{path}?t=forged').status_code, 404)
        self.assertEqual(client.get(f'{path}?{adam_query}').status_code, 404)
        self.assertEqual(self.fetch(alice_url + 'x').status_code, 404)

    def test_expired_link_is_404(self):
        self.store_photo(self.alice, self.company_a)
        url = self.link(self.alice, self.adam, self.company_a)
        with mock.patch('time.time', return_value=time.time() + 1501):
            self.assertEqual(self.fetch(url).status_code, 404)

    def test_link_from_another_company_never_serves_the_photo(self):
        self.store_photo(self.alice, self.company_a)
        self.assertEqual(self.fetch(self.link(self.alice, self.bob, self.company_b)).status_code, 404)

    def test_photo_stored_under_another_company_is_not_served(self):
        carol = self.member('carol', self.company_a, self.company_b)
        self.store_photo(carol, self.company_a)
        self.assertEqual(self.fetch(self.link(carol, carol, self.company_a)).status_code, 200)
        self.assertEqual(self.fetch(self.link(carol, carol, self.company_b)).status_code, 404)

    def test_missing_file_is_404(self):
        value = self.store_photo(self.alice, self.company_a)
        url = self.link(self.alice, self.adam, self.company_a)
        os.unlink(os.path.join(self.root, value))
        self.assertEqual(self.fetch(url).status_code, 404)

    def test_legacy_photo_only_for_member_company(self):
        os.makedirs(os.path.join(self.media, 'employee_profile_photo'))
        content = image_bytes('JPEG')
        with open(os.path.join(self.media, 'employee_profile_photo', 'alice.jpeg'), 'wb') as handle:
            handle.write(content)
        self.user_da.photos[self.alice.id] = 'alice.jpeg'
        response = self.fetch(self.link(self.alice, self.adam, self.company_a))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(self.fetch(self.link(self.alice, self.bob, self.company_b)).status_code, 404)

    def test_legacy_value_cannot_traverse(self):
        with open(os.path.join(self.media, 'secret.png'), 'wb') as handle:
            handle.write(image_bytes())
        self.user_da.photos[self.alice.id] = '../secret.png'
        self.assertEqual(self.fetch(self.link(self.alice, self.alice, self.company_a)).status_code, 404)
