""" End-to-end checks of /api/companies/<uuid>/... through the real middleware
(company context), JWT authentication and the capability system. """

import io
import os
import shutil
import tempfile
import uuid
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient

from pTracker.api.company_documents.company_document_biz import CompanyDocumentBL
from pTracker.api.company_documents.company_document_biz import DocumentAccessDenied
from pTracker.common.company_context import ActiveCompany
from pTracker.common.company_context import clear_active_company
from pTracker.common.company_context import set_active_company
from pTracker.common.token_revocation import RevocableAccessToken
from pTracker.dataaccess.platform_access.capability_models import Capability
from pTracker.dataaccess.platform_access.document_models import CompanyDocument
from pTracker.dataaccess.platform_access.membership_models import Membership
from pTracker.dataaccess.platform_access.role_models import Role
from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Tenant


def png_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'blue').save(buffer, format='PNG')
    return buffer.getvalue()


PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


@mock.patch('pTracker.api.company_documents.company_document_biz.Logs')
class CompanyDocumentsApiTests(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        overrides = override_settings(COMPANY_DOCUMENT_STORAGE_ROOT=self.root)
        overrides.enable()
        self.addCleanup(overrides.disable)

        tenant = Tenant.objects.create(slug='t', name='Tenant')
        self.company_a = Company.objects.create(tenant=tenant, legal_name='A Ltd', short_name='A')
        self.company_b = Company.objects.create(tenant=tenant, legal_name='B Ltd', short_name='B')

        self.manager_a = self.member(self.company_a, 'manager_a', ['company.manage_documents'])
        self.viewer_a = self.member(self.company_a, 'viewer_a', ['company.view_documents'])
        self.employee_a = self.member(self.company_a, 'employee_a', [])
        self.manager_b = self.member(self.company_b, 'manager_b', ['company.manage_documents'])
        self.outsider = get_user_model().objects.create_user('outsider', password='x')

    def member(self, company, username, capabilities):
        user = get_user_model().objects.create_user(username, password='x')
        role = Role.objects.create(company=company, name=f'role-{username}')
        role.capabilities.set(Capability.objects.filter(code__in=capabilities))
        Membership.objects.create(user=user, company=company, role=role)
        return user

    def client_for(self, user):
        client = APIClient()
        if user is not None:
            client.credentials(HTTP_AUTHORIZATION=f'JWT {RevocableAccessToken.for_user(user)}')
        return client

    def docs_url(self, company):
        return f'/api/companies/{company.uuid}/documents/'

    def upload(self, user, company, name='report.pdf', content=PDF, **data):
        data['file'] = SimpleUploadedFile(name, content, content_type='application/octet-stream')
        return self.client_for(user).post(self.docs_url(company), data, format='multipart')

    def stored_path(self, company, document):
        return os.path.join(self.root, str(company.uuid), document.storage_key)

    # Company UUID

    def test_companies_get_distinct_server_generated_uuids(self, _logs):
        self.assertIsInstance(self.company_a.uuid, uuid.UUID)
        self.assertNotEqual(self.company_a.uuid, self.company_b.uuid)
        before = self.company_a.uuid
        Company.objects.filter(pk=self.company_a.pk).update(legal_name='A Renamed')
        self.company_a.refresh_from_db()
        self.assertEqual(self.company_a.uuid, before)

    # Upload

    def test_manager_uploads_document(self, _logs):
        response = self.upload(self.manager_a, self.company_a, '../../Q3 report.pdf', description='Q3')
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()['document']
        self.assertEqual(body['original_filename'], 'Q3 report.pdf')
        self.assertEqual(body['content_type'], 'application/pdf')
        self.assertEqual(body['classification'], 'confidential')
        self.assertEqual(body['content_url'],
                         f"/api/companies/{self.company_a.uuid}/documents/{body['id']}/content/")
        self.assertNotIn(self.root, response.content.decode())
        self.assertNotIn('storage_key', body)

        document = CompanyDocument.objects.get(pk=body['id'])
        self.assertEqual(document.company_id, self.company_a.id)
        self.assertEqual(document.uploaded_by_id, self.manager_a.id)
        self.assertRegex(document.storage_key, r'^documents/[0-9a-f]{32}\.pdf$')
        with open(self.stored_path(self.company_a, document), 'rb') as handle:
            self.assertEqual(handle.read(), PDF)

    def test_upload_requires_manage_capability(self, _logs):
        for user in (self.viewer_a, self.employee_a):
            with self.subTest(user=user.username):
                self.assertEqual(self.upload(user, self.company_a).status_code, 403)
        self.assertEqual(CompanyDocument.objects.count(), 0)

    def test_unauthenticated_and_non_members_are_rejected(self, _logs):
        self.assertEqual(self.upload(None, self.company_a).status_code, 401)
        self.assertEqual(self.client_for(None).get(self.docs_url(self.company_a)).status_code, 401)
        self.assertEqual(self.upload(self.outsider, self.company_a).status_code, 403)

    def test_cannot_upload_into_another_company_by_changing_url(self, _logs):
        response = self.upload(self.manager_b, self.company_a)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(CompanyDocument.objects.count(), 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, str(self.company_a.uuid))))

    def test_company_header_for_foreign_company_is_rejected(self, _logs):
        client = self.client_for(self.manager_b)
        response = client.get(self.docs_url(self.company_a), HTTP_X_COMPANY_ID=str(self.company_a.id))
        self.assertEqual(response.status_code, 403)

    def test_invalid_uploads_are_rejected(self, _logs):
        cases = [
            ('fake.pdf', b'<script>alert(1)</script>', {}),
            ('logo.svg', b'<svg xmlns="http://www.w3.org/2000/svg"/>', {}),
            ('report.pdf', PDF, {'category': 'profile'}),
            ('report.pdf', PDF, {'category': '../../etc'}),
            ('report.pdf', PDF, {'classification': 'public'}),
            ('empty.pdf', b'', {}),
        ]
        for name, content, data in cases:
            with self.subTest(name=name, data=data):
                self.assertEqual(self.upload(self.manager_a, self.company_a, name, content, **data).status_code, 400)
        self.assertEqual(CompanyDocument.objects.count(), 0)

    @override_settings(COMPANY_DOCUMENT_MAX_UPLOAD_BYTES=10)
    def test_oversized_upload_is_rejected(self, _logs):
        self.assertEqual(self.upload(self.manager_a, self.company_a).status_code, 400)

    def test_failed_record_removes_written_file(self, _logs):
        with mock.patch('pTracker.dataaccess.platform_access.document_da.CompanyDocumentDA.create_document',
                        side_effect=RuntimeError('db down')):
            response = self.upload(self.manager_a, self.company_a)
        self.assertEqual(response.status_code, 500)
        directory = os.path.join(self.root, str(self.company_a.uuid), 'documents')
        self.assertEqual(os.listdir(directory), [])

    # Retrieval

    def test_viewer_downloads_with_safe_headers(self, _logs):
        document_id = self.upload(self.manager_a, self.company_a, 'evil"name.pdf').json()['document']['id']
        response = self.client_for(self.viewer_a).get(f'{self.docs_url(self.company_a)}{document_id}/content/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), PDF)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        self.assertIn('evil\\"name.pdf', response['Content-Disposition'])

    def test_classification_limits_who_can_read(self, _logs):
        ids = {}
        for classification in ('internal', 'confidential', 'restricted'):
            response = self.upload(self.manager_a, self.company_a, classification=classification)
            ids[classification] = response.json()['document']['id']

        expected = {
            self.employee_a: {'internal'},
            self.viewer_a: {'internal', 'confidential'},
            self.manager_a: {'internal', 'confidential', 'restricted'},
        }
        for user, readable in expected.items():
            client = self.client_for(user)
            listed = {d['classification'] for d in client.get(self.docs_url(self.company_a)).json()['documents']}
            self.assertEqual(listed, readable, user.username)
            for classification, document_id in ids.items():
                status = client.get(f'{self.docs_url(self.company_a)}{document_id}/content/').status_code
                self.assertEqual(status, 200 if classification in readable else 404,
                                 f'{user.username} {classification}')

    def test_other_company_cannot_read_by_guessing_ids(self, _logs):
        document_id = self.upload(self.manager_a, self.company_a).json()['document']['id']
        client = self.client_for(self.manager_b)
        # Their own company UUID with A's document id
        self.assertEqual(client.get(f'{self.docs_url(self.company_b)}{document_id}/content/').status_code, 404)
        self.assertEqual(client.get(f'{self.docs_url(self.company_b)}{document_id}/').status_code, 404)
        # A's company UUID in the URL
        self.assertEqual(client.get(f'{self.docs_url(self.company_a)}{document_id}/content/').status_code, 404)
        self.assertEqual(client.get(self.docs_url(self.company_a)).status_code, 404)
        # A random id in their own company
        self.assertEqual(client.get(f'{self.docs_url(self.company_b)}{uuid.uuid4()}/content/').status_code, 404)
        self.assertEqual(client.get(self.docs_url(self.company_b)).json()['documents'], [])

    def test_malformed_ids_do_not_route(self, _logs):
        client = self.client_for(self.manager_a)
        for path in (f'/api/companies/{self.company_a.id}/documents/',
                     f'{self.docs_url(self.company_a)}..%2F..%2Fetc%2Fpasswd/content/',
                     f'{self.docs_url(self.company_a)}../../etc/passwd/content/'):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 404)

    def test_missing_file_is_reported_not_crashed(self, _logs):
        body = self.upload(self.manager_a, self.company_a).json()['document']
        document = CompanyDocument.objects.get(pk=body['id'])
        os.unlink(self.stored_path(self.company_a, document))
        response = self.client_for(self.manager_a).get(body['content_url'])
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'file_missing')
        self.assertNotIn(self.root, response.content.decode())

    # Delete

    def test_delete_requires_manage_and_removes_file(self, _logs):
        body = self.upload(self.manager_a, self.company_a, classification='internal').json()['document']
        document = CompanyDocument.objects.get(pk=body['id'])
        path = self.stored_path(self.company_a, document)
        detail = f"{self.docs_url(self.company_a)}{body['id']}/"

        self.assertEqual(self.client_for(self.employee_a).delete(detail).status_code, 403)
        self.assertEqual(self.client_for(self.manager_b).delete(detail).status_code, 404)
        self.assertTrue(os.path.exists(path))

        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client_for(self.manager_a).delete(detail).status_code, 200)
        self.assertFalse(CompanyDocument.objects.filter(pk=body['id']).exists())
        self.assertFalse(os.path.exists(path))

    # Logo

    def test_logo_replace_view_and_delete(self, _logs):
        logo_url = f'/api/companies/{self.company_a.uuid}/logo/'
        manager = self.client_for(self.manager_a)

        upload = lambda client: client.put(  # noqa: E731
            logo_url, {'file': SimpleUploadedFile('logo.png', png_bytes())}, format='multipart')
        self.assertEqual(upload(self.client_for(self.employee_a)).status_code, 403)
        self.assertEqual(upload(self.client_for(self.manager_b)).status_code, 404)

        first = upload(manager)
        self.assertEqual(first.status_code, 200, first.content)
        old_path = self.stored_path(self.company_a, CompanyDocument.objects.get(pk=first.json()['logo']['id']))
        self.assertIn(f'{self.company_a.uuid}/profile/', old_path)

        with self.captureOnCommitCallbacks(execute=True):
            second = upload(manager)
        self.assertEqual(CompanyDocument.objects.filter(category='profile').count(), 1)
        self.assertFalse(os.path.exists(old_path))

        # Every member may view the logo, inline; other companies may not.
        response = self.client_for(self.employee_a).get(logo_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.client_for(self.manager_b).get(logo_url).status_code, 404)

        bad = manager.put(logo_url, {'file': SimpleUploadedFile('logo.pdf', PDF)}, format='multipart')
        self.assertEqual(bad.status_code, 400)

        current_path = self.stored_path(self.company_a, CompanyDocument.objects.get(pk=second.json()['logo']['id']))
        self.assertEqual(self.client_for(self.employee_a).delete(logo_url).status_code, 403)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(manager.delete(logo_url).status_code, 200)
        self.assertEqual(manager.get(logo_url).status_code, 404)
        self.assertFalse(os.path.exists(current_path))

    # Trusted processing (AI) accessor

    def test_processing_accessor_enforces_same_rules(self, _logs):
        body = self.upload(self.manager_a, self.company_a, 'notes.txt', b'hello ai', classification='restricted')
        document_id = body.json()['document']['id']
        try:
            set_active_company(ActiveCompany(self.manager_a.id, self.company_a.id, 'A'))
            self.assertEqual(
                CompanyDocumentBL().extract_document_text(self.manager_a.id, self.company_a.uuid, document_id),
                'hello ai')
            # Restricted: a viewer of the same company is refused
            set_active_company(ActiveCompany(self.viewer_a.id, self.company_a.id, 'A'))
            with self.assertRaises(DocumentAccessDenied):
                CompanyDocumentBL().read_document_for_processing(self.viewer_a.id, self.company_a.uuid, document_id)
            # Another company's user
            set_active_company(ActiveCompany(self.manager_b.id, self.company_b.id, 'B'))
            with self.assertRaises(DocumentAccessDenied):
                CompanyDocumentBL().read_document_for_processing(self.manager_b.id, self.company_a.uuid, document_id)
            # A user id that is not the request's verified user
            with self.assertRaises(DocumentAccessDenied):
                CompanyDocumentBL().read_document_for_processing(self.manager_a.id, self.company_a.uuid, document_id)
        finally:
            clear_active_company()

    def test_access_snapshot_exposes_company_uuid(self, _logs):
        response = self.client_for(self.employee_a).get('/api/auth/me/access/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['company']['uuid'], str(self.company_a.uuid))
