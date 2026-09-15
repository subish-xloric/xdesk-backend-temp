from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import default, slugify
import uuid

#digital mesh wikipedia tables
ACTIVE = (('0', 'Inactive',), ('1', 'Active',))
class WikiCategories(models.Model):
    category = models.CharField(max_length=255)
    category_description = models.CharField(max_length=500, blank=True, null=True)
    category_icon = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    created_by = models.IntegerField()
    active = models.CharField(max_length=1,choices=ACTIVE,default=1)

    def __str__(self):
        return self.category

    class Meta:
        db_table = 'wiki_categories'
        ordering = ['-id']


class WikiSubCategories(models.Model):
    category = models.ForeignKey(WikiCategories, on_delete=models.CASCADE, blank=True, null=True)
    sub_category = models.CharField(max_length=255)
    sub_category_description = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    created_by =  models.IntegerField()
    active = models.CharField(max_length=1,choices=ACTIVE,default=1)

    def __str__(self):
        return self.sub_category
            
    class Meta:
        db_table = 'wiki_sub_categories'


class WikiPages(models.Model):
    category = models.ForeignKey(WikiCategories, models.CASCADE, blank=True, null=True)
    sub_category_id = models.IntegerField(blank=True, null=True)
    page_heading = models.CharField(max_length=255)
    page_content = models.TextField()
    short_description = models.CharField(max_length=500, blank=True, null=True)
    approver = models.IntegerField(blank=True, null=True)
    approved_by = models.IntegerField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    created_by =  models.IntegerField(blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    status = models.IntegerField()
    tags = models.CharField(max_length=255, blank=True, null=True)
    permalink = models.SlugField()
    active = models.CharField(max_length=1,choices=ACTIVE,default=1)
    last_updated_at = models.DateTimeField(auto_now_add=True,blank=True, null=True)
    last_updated_by = models.IntegerField()
    is_confidential = models.IntegerField(blank=True, null=True, default=0)

    def save(self, *args, **kwargs):
        self.permalink = slugify(self.page_heading)
        super(WikiPages, self).save(*args, **kwargs)

    class Meta:
        db_table = 'wiki_pages'
        ordering = ['-id']


class WikiEditedPages(models.Model):
    page = models.ForeignKey(WikiPages, models.DO_NOTHING)
    category = models.ForeignKey(WikiCategories, models.DO_NOTHING)
    sub_category_id = models.IntegerField(blank=True, null=True)
    page_heading = models.CharField(max_length=255)
    page_content = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)
    approver = models.IntegerField(blank=True, null=True)
    approved_by = models.IntegerField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    created_by = models.IntegerField(blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    status = models.IntegerField()
    tags = models.CharField(max_length=255, blank=True, null=True)
    permalink = models.CharField(max_length=250, blank=True, null=True)
    active = models.IntegerField(default=1)
    is_confidential = models.IntegerField(blank=True, null=True, default=0)

    class Meta:
        managed = False
        db_table = 'wiki_edited_pages'

# class WikiEditedPages(models.Model):
#     page = models.ForeignKey(WikiPages, models.DO_NOTHING, blank=True, null=True)
#     page_heading = models.CharField(max_length=255)
#     page_content = models.TextField()
#     short_description = models.CharField(max_length=500, blank=True, null=True)
#     approver = models.IntegerField(blank=True, null=True)
#     approved_by = models.IntegerField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True, blank=True)
#     created_by = models.IntegerField(blank=True, null=True)
#     remarks = models.CharField(max_length=500, blank=True, null=True)
#     status = models.IntegerField()

#     class Meta:
#         db_table = 'wiki_edited_pages'


class WikiPageHistory(models.Model):
    page = models.ForeignKey(WikiPages, models.DO_NOTHING, blank=True, null=True)
    category = models.ForeignKey(WikiCategories, models.DO_NOTHING)
    sub_category_id = models.IntegerField(blank=True, null=True)
    page_heading = models.CharField(max_length=255)
    page_content = models.TextField()
    short_description = models.CharField(max_length=500, blank=True, null=True)
    approver = models.IntegerField(blank=True, null=True)
    approved_by = models.IntegerField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    created_by =  models.IntegerField(blank=True, null=True)
    histroy_created_at = models.DateTimeField(auto_now_add=True, blank=True)
    permalink = models.CharField(max_length=150, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    status = models.IntegerField()
    last_updated_at = models.DateTimeField(blank=True, null=True)
    last_updated_by = models.IntegerField()
    is_confidential = models.IntegerField(blank=True, null=True, default=0)
    class Meta:
        db_table = 'wiki_page_history'


class WikiPageLikes(models.Model):
    page = models.ForeignKey(WikiPages, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    is_liked = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    
    class Meta:
        db_table = 'wiki_page_likes'


class WikiPopularTags(models.Model):
    tag = models.CharField(max_length=100)
    clicked = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True)

    class Meta:
        db_table = 'wiki_popular_tags'


class WikiLogs(models.Model):
    log_id = models.AutoField(primary_key=True)
    message = models.TextField(blank=True, null=True)
    log_type = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)

    class Meta:
        db_table = 'wiki_logs'

def upload_path_handler(instance, filename):
    return f"wiki/attachments/article-{instance.page.id}/{filename}"

class WikiPageAttachments(models.Model):
    page = models.ForeignKey(WikiPages, models.DO_NOTHING)
    attachments = models.FileField(upload_to=upload_path_handler)
    created_by = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    
    class Meta:
        db_table = 'wiki_page_attachments'
        ordering = ['-id']


class AuditLogs(models.Model):
    audit_logs_id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    organization_id = models.IntegerField()
    event = models.CharField(max_length=250, blank=True, null=True)
    event_details = models.CharField(max_length=500, blank=True, null=True)
    created_date_time = models.DateTimeField(auto_now_add=True, blank=True)

    class Meta:
        managed = False
        db_table = 'audit_logs'


class WikiAllPagesView(models.Model):
    tbl = models.CharField(max_length=6)
    page_id = models.IntegerField()
    category_id = models.IntegerField(blank=True, null=True)
    sub_category_id = models.IntegerField(blank=True, null=True)
    page_heading = models.CharField(max_length=255)
    page_content = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)
    approver = models.IntegerField(blank=True, null=True)
    approved_by = models.IntegerField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    created_by = models.IntegerField(blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    status = models.IntegerField()
    tags = models.CharField(max_length=255, blank=True, null=True)
    permalink = models.CharField(max_length=250, blank=True, null=True)
    active = models.IntegerField()
    last_updated_at = models.CharField(max_length=19, blank=True, null=True)
    last_updated_by = models.CharField(max_length=11)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'wiki_all_pages_view'


