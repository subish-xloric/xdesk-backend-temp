import uuid

from django.conf import settings
from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
""" The following tables are created here
CompanyDocument

Metadata for a file kept in the company's confidential storage directory
(pTracker/common/confidential_storage.py). Only the relative storage_key is
stored; the absolute path is built by the storage service and never leaves it.
"""


class CompanyDocument(models.Model):
    CATEGORY_PROFILE = 'profile'
    CATEGORY_DOCUMENTS = 'documents'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = (
        (CATEGORY_PROFILE, 'Profile'),
        (CATEGORY_DOCUMENTS, 'Documents'),
        (CATEGORY_OTHER, 'Other'),
    )

    # Who may read it (see CompanyDocumentBL): internal = any active member,
    # confidential = company.view_documents, restricted = company.manage_documents.
    CLASSIFICATION_INTERNAL = 'internal'
    CLASSIFICATION_CONFIDENTIAL = 'confidential'
    CLASSIFICATION_RESTRICTED = 'restricted'
    CLASSIFICATION_CHOICES = (
        (CLASSIFICATION_INTERNAL, 'Internal'),
        (CLASSIFICATION_CONFIDENTIAL, 'Confidential'),
        (CLASSIFICATION_RESTRICTED, 'Restricted'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='documents')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES,
        default=CLASSIFICATION_CONFIDENTIAL)
    storage_key = models.CharField(max_length=255, unique=True,
        help_text="<category>/<generated name>, relative to the company's storage directory")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    description = models.CharField(max_length=1000, blank=True, default='')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='uploaded_company_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_company_document'
        indexes = [
            models.Index(fields=['company', 'category', '-created_at'], name='pcd_company_category_idx'),
        ]

    def __str__(self):
        return f'{self.company_id}:{self.category}:{self.original_filename}'
