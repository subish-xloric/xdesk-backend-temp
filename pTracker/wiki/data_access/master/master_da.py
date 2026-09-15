from django.forms.utils import ErrorDict
from pTracker.wiki.data_access.wiki_models.models import WikiPages
from pTracker.wiki.data_access.wiki_models.models import WikiPageHistory
from pTracker.wiki.data_access.wiki_models.models import WikiEditedPages
from pTracker.wiki.data_access.wiki_models.models import WikiPageLikes
from pTracker.wiki.data_access.wiki_models.models import WikiPopularTags
from pTracker.wiki.data_access.wiki_models.models import WikiPageAttachments
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from django.db import transaction
from django.utils import timezone
import os
from django.conf import settings
class MasterData():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()

    # @transaction.atomic
    def create_page(self, data, files):
        try:
            page_obj = WikiPages.objects.create(
                category_id = data.category,
                sub_category_id = data.sub_category,
                page_heading = data.page_heading,
                page_content = data.page_content,
                short_description = data.short_description,
                tags = data.tags,
                status = data.status,
                created_by = data.created_by,
                approver = data.approver,
                approved_by = data.approved_by,
                approved_at = data.approved_at,
                last_updated_by = data.created_by,
                is_confidential = data.is_confidential
            )
            page_obj.save()
            if files:
                for f in files.getlist('attachment[]'):
                    try:
                        WikiPageAttachments.objects.create(page_id=page_obj.id,attachments = f, created_by=data.created_by)
                    except Exception as error:
                        self.__log.error(
                            f'Error in the method  create_page(WikiPageAttachments) in MasterData(master)., Error: {str(error)},'
                            f'Error traceback: {self.__exception.exception()}'
                        )
        except Exception as error:
            self.__log.error(
                f'Error in the method method create_page in MasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page_obj = None
        return page_obj


    def create_attachments(self,data,files):
        try:
            created = False
            if files:
                for f in files.getlist('attachment[]'):
                    WikiPageAttachments.objects.create(page_id=data.page_id,attachments = f, created_by=data.created_by)
                    created = True
        except Exception as error:
            self.__log.error(
                f'Error in the method method create_attachments in MasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            created = False
        return created

    def delete_attahcments(self,id):
        try:
            attachment = WikiPageAttachments.objects.get(id=id)
            if os.path.exists(os.path.join(settings.MEDIA_ROOT, f'{attachment.attachments}')):
                 os.remove(os.path.join(settings.MEDIA_ROOT, f'{attachment.attachments}'))
            attachment.delete()
        except Exception as error:
            self.__log.error(
                f'Error in the method  delete_attahcments in MasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            attachment = False
        return attachment

    def create_edited_page(self, data, data_from , article_status):
        try:
            page = False
            if data_from == 'wiki_pages' and article_status in [0,2]:
                wiki_page, created = WikiPages.objects.update_or_create(
                id = data.page_id,
                created_by = data.created_by,
                defaults={
                        'category_id' : data.category_id,
                        'sub_category_id' : data.sub_category_id,
                        'page_content' : data.page_content,
                        'short_description' : data.short_description,
                        'tags' : data.tags,
                        'status' : data.status,
                        'approver' : data.approver,
                        'created_by' : data.created_by,
                        'created_at' : timezone.now(),
                        'approved_by' : data.approved_by,
                        'approved_at' : data.approved_at,
                        'last_updated_by' : data.created_by,
                        'is_confidential' : data.is_confidential,
                        'remarks':''
                    },
                )
                page = wiki_page
            else:
                edited_page, created = WikiEditedPages.objects.update_or_create(
                page_id = data.page_id,
                created_by = data.created_by,
                defaults={
                        'page_id' : data.page_id,
                        'category_id' : data.category_id,
                        'sub_category_id' : data.sub_category_id,
                        'page_content' : data.page_content,
                        'short_description' : data.short_description,
                        'tags' : data.tags,
                        'status' : data.status,
                        'approver' : data.approver,
                        'created_by' : data.created_by,
                        'created_at' : timezone.now(),
                        'approved_by' : data.approved_by,
                        'approved_at' : data.approved_at,
                        'is_confidential' : data.is_confidential,
                        'active': 1,
                        'remarks':''
                    },
                )
                # move data to page_history if status == 1
                if int(edited_page.status) == 1:
                    wiki_pages = WikiPages.objects.get(id = edited_page.page_id)
                    page_history = WikiPageHistory.objects.create(
                                    page_id = wiki_pages.id,
                                    category_id = wiki_pages.category_id,
                                    sub_category_id = wiki_pages.sub_category_id,
                                    page_heading = wiki_pages.page_heading,
                                    page_content  = wiki_pages.page_content,
                                    short_description = wiki_pages.short_description,
                                    tags = wiki_pages.tags,
                                    created_at = wiki_pages.created_at,
                                    created_by = wiki_pages.created_by,
                                    last_updated_by = wiki_pages.last_updated_by,
                                    last_updated_at = wiki_pages.last_updated_at,
                                    approver = wiki_pages.approver,
                                    approved_by = wiki_pages.approved_by,
                                    approved_at = wiki_pages.approved_at,
                                    status = wiki_pages.status,
                                    is_confidential = wiki_pages.is_confidential,
                                    permalink = wiki_pages.permalink)
                    page_history.save()
                    wiki_pages.category_id = edited_page.category_id
                    wiki_pages.sub_category_id = edited_page.sub_category_id
                    wiki_pages.tags = edited_page.tags
                    wiki_pages.page_content = edited_page.page_content
                    wiki_pages.last_updated_by = edited_page.created_by
                    wiki_pages.last_updated_at = edited_page.created_at
                    wiki_pages.approver = edited_page.approver
                    wiki_pages.approved_by = edited_page.approved_by
                    wiki_pages.approved_at = edited_page.approved_at
                    wiki_pages.short_description = edited_page.short_description
                    wiki_pages.is_confidential = edited_page.is_confidential
                    wiki_pages.save()
                page = edited_page
        except Exception as error:
            self.__log.error(
                f'Error in the method method create_edited_page in MasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page = False
        return  page


    def create_liked_page(self, data):
        try:
            obj, created = WikiPageLikes.objects.update_or_create(
                page_id = data.page_id,
                user_id = data.user_id,
                defaults={
                        'page_id' : data.page_id,
                        'user_id' : data.user_id,
                        'is_liked' : data.is_liked
                },
            )
            created = True
        except Exception as error:
            self.__log.error(
                f'Error in the method method create_liked_page in MasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            created = False
        return  created
    

    def create_popular_tags(self,tag):
        try:
            tags = WikiPopularTags.objects.filter(tag=tag)
            if tags:
                tags = WikiPopularTags.objects.get(tag=tag)
            else:
                tags = WikiPopularTags()
            tags.tag = tag
            tags.clicked = int(tags.clicked if tags.clicked else 0 )+1
            tags.save()
        except Exception as error:
            self.__log.error(
                f'Error in the method method create_popular_tags in MasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            tags = None
        return tags

