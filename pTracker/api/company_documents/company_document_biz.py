""" Company confidential documents and the company logo.

Authorization, on every call:
1. The company comes from the caller's verified active membership
   (ModuleGateMiddleware / company_context), never from the URL. The company
   UUID in the URL must equal that company's UUID, otherwise the response is
   404 - the same as for an unknown company, so ids cannot be probed.
2. Documents are only looked up inside that company and inside the
   classifications the caller may read; anything else is 404.
3. Reading: internal -> any active member; confidential ->
   company.view_documents; restricted -> company.manage_documents.
   Writing (upload, replace logo, delete) -> company.manage_documents.
"""

from django.conf import settings
from django.db import transaction
from django.http import FileResponse
from django.urls import reverse

from pTracker.common.company_authorization import has_capability
from pTracker.common.company_context import get_active_company
from pTracker.common.confidential_storage import CompanyFileStorage
from pTracker.common.confidential_storage import FileTooLarge
from pTracker.common.confidential_storage import StorageError
from pTracker.common.confidential_storage import StoredFileMissing
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.upload_validation import DOCUMENT_TYPES
from pTracker.common.upload_validation import IMAGE_TYPES
from pTracker.common.upload_validation import UploadRejected
from pTracker.common.upload_validation import clean_filename
from pTracker.common.upload_validation import validate_upload
from pTracker.dataaccess.platform_access.document_da import CompanyDocumentDA
from pTracker.dataaccess.platform_access.document_models import CompanyDocument
from pTracker.dataaccess.platform_access.tenancy_da import TenancyDA

CAP_VIEW = 'company.view_documents'
CAP_MANAGE = 'company.manage_documents'

UPLOAD_CATEGORIES = (CompanyDocument.CATEGORY_DOCUMENTS, CompanyDocument.CATEGORY_OTHER)
CLASSIFICATIONS = tuple(code for code, _ in CompanyDocument.CLASSIFICATION_CHOICES)

NOT_FOUND = {'error': 'Not found', 'status': 404}
FORBIDDEN = {'error': 'You do not have permission to perform this action', 'status': 403}
NO_COMPANY = {'error': 'Select a company first (X-Company-Id header)', 'code': 'company_required', 'status': 403}
STORAGE_UNAVAILABLE = {'error': 'Document storage is temporarily unavailable', 'status': 503}


class DocumentAccessDenied(Exception):
    """ Raised by the processing accessors; carries the response dict. """

    def __init__(self, response):
        super().__init__(response.get('error'))
        self.response = response


class CompanyDocumentBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__da = CompanyDocumentDA()
        self.__storage = CompanyFileStorage()

    # Documents

    def list_documents(self, user_id, company_uuid, params):
        company, error = self.__company(user_id, company_uuid)
        if error:
            return error
        category = params.get('category')
        if category and category not in dict(CompanyDocument.CATEGORY_CHOICES):
            return {'error': 'Unknown category', 'status': 400}
        documents = self.__da.get_documents(company.id, self.__readable(user_id), category)
        return {'documents': [self.__document_dict(company, d) for d in documents], 'status': 200}

    def get_document(self, user_id, company_uuid, document_id):
        company, error = self.__company(user_id, company_uuid)
        if error:
            return error
        document = self.__da.get_document(company.id, document_id, self.__readable(user_id))
        if not document:
            return NOT_FOUND
        return {'document': self.__document_dict(company, document), 'status': 200}

    def upload_document(self, user_id, company_uuid, data, files):
        company, error = self.__company(user_id, company_uuid)
        if error:
            return error
        if not has_capability(user_id, CAP_MANAGE):
            return FORBIDDEN

        category = data.get('category') or CompanyDocument.CATEGORY_DOCUMENTS
        if category not in UPLOAD_CATEGORIES:
            return {'error': f"category must be one of: {', '.join(UPLOAD_CATEGORIES)}", 'status': 400}
        classification = data.get('classification') or CompanyDocument.CLASSIFICATION_CONFIDENTIAL
        if classification not in CLASSIFICATIONS:
            return {'error': f"classification must be one of: {', '.join(CLASSIFICATIONS)}", 'status': 400}
        description = (data.get('description') or '').strip()
        if len(description) > 1000:
            return {'error': 'description must be at most 1000 characters', 'status': 400}

        result = self.__store(user_id, company, files.get('file'), category, classification, description,
                              DOCUMENT_TYPES, settings.COMPANY_DOCUMENT_MAX_UPLOAD_BYTES)
        if 'error' in result:
            return result
        return {'document': self.__document_dict(company, result['document']), 'status': 201}

    def delete_document(self, user_id, company_uuid, document_id):
        company, error = self.__company(user_id, company_uuid)
        if error:
            return error
        # Check existence first so a non-manager cannot tell which ids exist.
        document = self.__da.get_document(company.id, document_id, self.__readable(user_id))
        if not document:
            return NOT_FOUND
        if not has_capability(user_id, CAP_MANAGE):
            return FORBIDDEN
        self.__delete_records(company, [document])
        return {'message': 'Document deleted', 'status': 200}

    def document_content(self, user_id, company_uuid, document_id):
        """ FileResponse on success, else a response dict. Always an attachment. """
        company, error = self.__company(user_id, company_uuid)
        if error:
            return error
        document = self.__da.get_document(company.id, document_id, self.__readable(user_id))
        if not document:
            return NOT_FOUND
        return self.__file_response(company, document, as_attachment=True)

    # Logo (category "profile", one per company, readable by every member)

    def logo_content(self, user_id, company_uuid):
        company, error = self.__company(user_id, company_uuid)
        if error:
            return error
        document = self.__da.get_latest_profile_document(company.id)
        if not document:
            return NOT_FOUND
        return self.__file_response(company, document, as_attachment=False)

    def replace_logo(self, user_id, company_uuid, files):
        company, error = self.__company(user_id, company_uuid)
        if error:
            return error
        if not has_capability(user_id, CAP_MANAGE):
            return FORBIDDEN

        result = self.__store(user_id, company, files.get('file'), CompanyDocument.CATEGORY_PROFILE,
                              CompanyDocument.CLASSIFICATION_INTERNAL, '', IMAGE_TYPES,
                              settings.COMPANY_LOGO_MAX_UPLOAD_BYTES, replace_profile=True)
        if 'error' in result:
            return result
        return {'logo': self.__document_dict(company, result['document']), 'status': 200}

    def delete_logo(self, user_id, company_uuid):
        company, error = self.__company(user_id, company_uuid)
        if error:
            return error
        if not has_capability(user_id, CAP_MANAGE):
            return FORBIDDEN
        with transaction.atomic():
            documents = self.__da.get_profile_documents_for_update(company.id)
            if not documents:
                return NOT_FOUND
            self.__delete_records(company, documents)
        return {'message': 'Logo deleted', 'status': 200}

    # Trusted processing (e.g. AI document analysis). Not exposed over HTTP:
    # a workflow passes a document id it was given, and the same checks as the
    # download endpoint run before any content leaves storage. Raise
    # DocumentAccessDenied rather than returning content on any failure.

    def read_document_for_processing(self, user_id, company_uuid, document_id):
        """ (document, bytes) for an authorized caller. """
        company, document = self.__authorized_document(user_id, company_uuid, document_id)
        try:
            return document, self.__storage.read(company.uuid, document.storage_key)
        except StoredFileMissing:
            self.__log.error(f'Company document file missing: document={document.id}')
            raise DocumentAccessDenied(NOT_FOUND) from None
        except StorageError as error:
            self.__log.error(f'Company document read failed: document={document.id}: {error}')
            raise DocumentAccessDenied(STORAGE_UNAVAILABLE) from None

    def extract_document_text(self, user_id, company_uuid, document_id, max_chars=20000):
        """ Plain text of a PDF/TXT/CSV document, truncated to max_chars, for
        building model context. Other types (images, Office) need an OCR or
        conversion service that is not part of this backend yet -> None. """
        document, content = self.read_document_for_processing(user_id, company_uuid, document_id)
        if document.content_type in ('text/plain', 'text/csv'):
            text = content.decode('utf-8', errors='replace')
        elif document.content_type == 'application/pdf':
            text = self.__pdf_text(document, content)
        else:
            return None
        return text[:max_chars]

    # Helpers

    def __company(self, user_id, company_uuid):
        """ (company, None) when the URL's company is the caller's verified
        active company, else (None, response dict). """
        active = get_active_company()
        if active is None or active.user_id != user_id:
            return None, NO_COMPANY
        company = TenancyDA().get_company_by_id(active.company_id)
        if company is None or str(company.uuid) != str(company_uuid):
            return None, NOT_FOUND
        return company, None

    def __readable(self, user_id):
        """ Classifications the caller may read in the active company. """
        if has_capability(user_id, CAP_MANAGE):
            return CLASSIFICATIONS
        if has_capability(user_id, CAP_VIEW):
            return (CompanyDocument.CLASSIFICATION_INTERNAL, CompanyDocument.CLASSIFICATION_CONFIDENTIAL)
        return (CompanyDocument.CLASSIFICATION_INTERNAL,)

    def __authorized_document(self, user_id, company_uuid, document_id):
        company, error = self.__company(user_id, company_uuid)
        if error:
            raise DocumentAccessDenied(error)
        document = self.__da.get_document(company.id, document_id, self.__readable(user_id))
        if not document:
            raise DocumentAccessDenied(NOT_FOUND)
        return company, document

    def __store(self, user_id, company, upload, category, classification, description, allowed_types,
            max_bytes, replace_profile=False):
        """ Validates and writes the file, then records it. The database row is
        created only after the file is complete; if the row cannot be saved the
        new file is removed again. Replaced logo files are removed only after
        the transaction commits. Returns {'document': ...} or an error dict. """
        try:
            file_type = validate_upload(upload, allowed_types, max_bytes)
        except UploadRejected as error:
            return {'error': str(error), 'status': 400}

        try:
            stored = self.__storage.save(company.uuid, category, upload.chunks(), file_type.extension, max_bytes)
        except FileTooLarge as error:
            return {'error': str(error), 'status': 400}
        except StorageError as error:
            self.__log.error(f'Company document write failed: company={company.id}: {error}')
            return STORAGE_UNAVAILABLE

        try:
            with transaction.atomic():
                replaced = self.__da.get_profile_documents_for_update(company.id) if replace_profile else []
                document = self.__da.create_document(
                    company_id=company.id,
                    category=category,
                    classification=classification,
                    storage_key=stored.storage_key,
                    original_filename=clean_filename(upload.name, file_type.extension),
                    content_type=file_type.content_type,
                    size=stored.size,
                    sha256=stored.sha256,
                    description=description,
                    uploaded_by_id=user_id,
                )
                if replaced:
                    self.__delete_records(company, replaced)
        except Exception:
            self.__remove_file(company, stored.storage_key)
            self.__log.error(f'Company document record failed: company={company.id}: '
                             f'{self.__exception.get_exception()}')
            return {'error': 'Could not save the document', 'status': 500}
        return {'document': document}

    def __delete_records(self, company, documents):
        """ Deletes the rows; the files go once the deletion is committed, so a
        rolled-back transaction never leaves a row pointing at a removed file. """
        keys = [d.storage_key for d in documents]
        self.__da.delete_documents([d.id for d in documents])
        transaction.on_commit(lambda: [self.__remove_file(company, key) for key in keys])

    def __remove_file(self, company, storage_key):
        try:
            self.__storage.delete(company.uuid, storage_key)
        except StorageError as error:
            # Left as an orphan; cleanup_company_documents reports it.
            self.__log.error(f'Company document file delete failed: company={company.id} '
                             f'key={storage_key}: {error}')

    def __file_response(self, company, document, as_attachment):
        try:
            handle = self.__storage.open(company.uuid, document.storage_key)
        except StoredFileMissing:
            self.__log.error(f'Company document file missing: document={document.id}')
            return {'error': 'The file for this document is missing', 'code': 'file_missing', 'status': 404}
        except StorageError as error:
            self.__log.error(f'Company document open failed: document={document.id}: {error}')
            return STORAGE_UNAVAILABLE

        response = FileResponse(handle, as_attachment=as_attachment, filename=document.original_filename,
                                content_type=document.content_type)
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        response['Content-Security-Policy'] = "default-src 'none'; sandbox"
        return response

    def __pdf_text(self, document, content):
        from io import BytesIO
        from PyPDF2 import PdfReader
        try:
            reader = PdfReader(BytesIO(content))
            return '\n'.join((page.extract_text() or '') for page in reader.pages)
        except Exception:
            self.__log.error(f'PDF text extraction failed: document={document.id}')
            return ''

    @staticmethod
    def __document_dict(company, document):
        if document.category == CompanyDocument.CATEGORY_PROFILE:
            content_url = reverse('company_logo', kwargs={'company_uuid': company.uuid})
        else:
            content_url = reverse('company_document_content',
                                  kwargs={'company_uuid': company.uuid, 'document_id': document.id})
        return {
            'id': str(document.id),
            'company_uuid': str(company.uuid),
            'category': document.category,
            'classification': document.classification,
            'original_filename': document.original_filename,
            'content_type': document.content_type,
            'size': document.size,
            'sha256': document.sha256,
            'description': document.description,
            'uploaded_by_id': document.uploaded_by_id,
            'created_at': document.created_at,
            'updated_at': document.updated_at,
            'content_url': content_url,
        }
