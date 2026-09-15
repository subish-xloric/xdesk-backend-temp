from typing import cast
from pTracker.wiki.data_access.wiki_models.models import WikiCategories, WikiPageHistory, WikiPages, WikiSubCategories
from pTracker.wiki.data_access.wiki_models.models import WikiEditedPages
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from django.contrib.auth.models import Group

class AdminMasterData():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()


    def update_page_status(self, data):
        try:
            page = WikiPages.objects.get(id = data.page_id)
            page.approved_by = data.approved_by
            page.approved_at = data.approved_at
            page.status = data.status
            page.remarks = data.remarks
            page.save()
        except Exception as error:
            self.__log.error(
                f'Error in the method  update_page_status in AdminMasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page = False
        return page


    def update_edited_page_status(self,data):
        try:
            page = False
            # update status on edited pages
            edited_page = WikiEditedPages.objects.get(id = data.page_id)
            edited_page.approved_by = data.approved_by
            edited_page.approved_at = data.approved_at
            edited_page.status = data.status
            edited_page.remarks = data.remarks
            edited_page.save()
            if edited_page:
                page = edited_page
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
                page = wiki_pages
        except Exception as error:
            self.__log.error(
                f'Error in the method  update_edited_page_status in AdminMasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page = False
        return page


    def create_categories(self,data):
        try:
            created = False
            category = WikiCategories.objects.create(
                        category = data.category,
                        category_description = data.category_description,
                        created_by = data.created_by,
                        active = data.active
                        )

            count = len(data.sub_category)
            if count > 0:
                  for x in range(count):
                    if data.sub_category[x]:
                        sub_category = WikiSubCategories.objects.create(
                                            category_id = category.id,
                                            sub_category = data.sub_category[x],
                                            sub_category_description = data.sub_category_description[x],
                                            created_by = data.created_by,
                                            active = data.sub_active[x]
                                            )
                        if sub_category:
                            created = True
            created = category
        except Exception as error:
            self.__log.error(
                f'Error in the method  create_categories in AdminMasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            created = False
        return created


    def update_categories(self,data):
        try:
            created = False
            category = WikiCategories.objects.get(id=data.category_id)
            category.category = data.category
            category.category_description = data.category_description
            category.created_by = data.created_by
            category.active = data.active
            category.save()

            if category:
                created =True
            count = len(data.sub_category)
            if count > 0:
                  for x in range(count):
                    if data.sub_category[x]:
                        if data.sub_category_id[x]:
                            sub_category_id = data.sub_category_id[x]
                        else:
                            try:
                                sub_category_id = WikiSubCategories.objects.all().order_by("-id")[0]
                                sub_category_id = int(sub_category_id.id)+1
                            except:
                                sub_category_id = 1

                        obj,sub_category = WikiSubCategories.objects.update_or_create(
                                            id = sub_category_id,
                                            category_id = category.id,
                                            defaults={
                                                'sub_category' : data.sub_category[x],
                                                'sub_category_description' : data.sub_category_description[x],
                                                'created_by' : data.created_by,
                                                'active' : data.sub_active[x]
                                            }
                                        )
                        if sub_category:
                            created = True
        except Exception as error:
            self.__log.error(
                f'Error in the method  update_categories in AdminMasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            created = False
        return created


    def remove_category(self,category):
        try:
            cate = WikiCategories.objects.get(id=category).delete()
        except Exception as error:
            self.__log.error(
                f'Error in the method  remove_category in AdminMasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            cate = False
        return cate


    def remove_sub_category(self,sub_category):
        try:
            cate = WikiSubCategories.objects.get(id=sub_category).delete()
        except Exception as error:
            self.__log.error(
                f'Error in the method  remove_sub_category in AdminMasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            cate = False
        return cate
    

    def remove_page(self,page_id):
        try:
            cate = WikiPages.objects.get(id=page_id)
            cate.active = 0
            cate.save()
        except Exception as error:
            self.__log.error(
                f'Error in the method  remove_page in AdminMasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            cate = False
        return cate
    

    def remove_edited_page(self,page_id):
        try:
            cate = WikiEditedPages.objects.get(id=page_id)
            cate.active = 0
            cate.save()
        except Exception as error:
            self.__log.error(
                f'Error in the method  remove_edited_page in AdminMasterData(master)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            cate = False
        return cate