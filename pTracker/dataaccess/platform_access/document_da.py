from pTracker.dataaccess.platform_access.document_models import CompanyDocument


class CompanyDocumentDA():

    def create_document(self, company_id, category, classification, storage_key, original_filename,
            content_type, size, sha256, description, uploaded_by_id):
        return CompanyDocument.objects.create(
            company_id=company_id,
            category=category,
            classification=classification,
            storage_key=storage_key,
            original_filename=original_filename,
            content_type=content_type,
            size=size,
            sha256=sha256,
            description=description,
            uploaded_by_id=uploaded_by_id,
        )

    def get_document(self, company_id, document_id, classifications):
        """ Only within the company and the classifications the caller may read,
        so a document outside them is indistinguishable from a missing one. """
        return CompanyDocument.objects.filter(
            pk=document_id, company_id=company_id, classification__in=classifications).first()

    def get_documents(self, company_id, classifications, category=None):
        documents = CompanyDocument.objects.filter(company_id=company_id, classification__in=classifications)
        if category:
            documents = documents.filter(category=category)
        return documents.order_by('-created_at')

    def get_profile_documents_for_update(self, company_id):
        """ Locks the company's current profile image rows (call inside atomic()). """
        return list(CompanyDocument.objects.select_for_update().filter(
            company_id=company_id, category=CompanyDocument.CATEGORY_PROFILE).order_by('-created_at'))

    def get_latest_profile_document(self, company_id):
        return CompanyDocument.objects.filter(
            company_id=company_id, category=CompanyDocument.CATEGORY_PROFILE).order_by('-created_at').first()

    def delete_documents(self, document_ids):
        CompanyDocument.objects.filter(pk__in=list(document_ids)).delete()

    def get_storage_keys(self, company_id):
        return set(CompanyDocument.objects.filter(company_id=company_id).values_list('storage_key', flat=True))
