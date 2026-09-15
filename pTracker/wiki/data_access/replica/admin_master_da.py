from django.db.models import Q
from django.db.models import Case, Count, When
from django.db.models import query
from django.db.models.query import QuerySet
from pTracker.wiki.data_access.wiki_models.models import WikiAllPagesView, WikiSubCategories, WikiCategories
from pTracker.wiki.data_access.wiki_models.models import WikiPages, WikiEditedPages
from pTracker.wiki.data_access.wiki_models.models import WikiPageLikes
from pTracker.wiki.data_access.wiki_models.models import WikiPopularTags
from pTracker.wiki.data_access.wiki_models.models import WikiPageAttachments
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from django.contrib.auth.models import User
from django.db import connection


class AdminMasterDA():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
    
    def get_all_users(self):
        try:
            users = User.objects.all().order_by('first_name')
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_all_pages_from_submitted in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            users = None
        return users


    def get_all_approvers(self):
        try:
            users = User.objects.filter(groups__id__lt = 5).order_by('first_name')
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_all_pages_from_submitted in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            users = None
        return users


    def get_all_pages_from_submitted(self,approver):
        try:
            pages = WikiPages.objects.filter(status=0,active=1).annotate(
                    relevancy=Count(
                    Case(When(approver=approver,
                    status=0, then=1)))).order_by('-relevancy','status','-created_at')
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_all_pages_from_submitted in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            pages = None
        return pages


    def get_all_pages_from_view(self,approver):
        try:
            pages = WikiAllPagesView.objects.filter(active=1).annotate(
                    relevancy=Count(
                    Case(When(approver=approver,
                    status=0, then=1)))).order_by('-relevancy','status','-created_at')
        except Exception as error:
            self.__log.error(
                f'Error in the method  get_all_pages_from_view in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            pages = None
        return pages


    def get_all_pages_from_edited(self,approver):
        try:
            pages = WikiEditedPages.objects.filter(status=0,active=1).annotate(
                    relevancy=Count(
                    Case(When(approver=approver,
                    status=0, then=1)))).order_by('-relevancy','status','-created_at')
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_all_pages_from_edited in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            pages = None
        return pages


    def get_single_page(self, page_id):
         try:
            page = WikiPages.objects.get(id=page_id)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_single_page in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page = None
         return page
    

    def get_single_edited_page(self, page_id):
         try:
            page = WikiEditedPages.objects.get(id=page_id)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_single_page in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page = None
         return page


    def get_all_page_categories(self):
        try:
            categories = WikiCategories.objects.all().order_by('category')
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_all_page_categories in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            categories = None
        return categories
    

    def get_single_category(self,category_id):
        try:
            categories = WikiCategories.objects.get(id=category_id)
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_single_category in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            categories = None
        return categories


    def get_all_sub_categories(self,category_id):
        try:
            categories = WikiSubCategories.objects.filter(category_id=category_id)
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_sub_categories in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            categories = None
        return categories

    
    def check_category_is_existed(self,category):
        try:
            categories = WikiCategories.objects.filter(category=category).exists()
        except Exception as error:
            self.__log.error(
                f'Error in the method method check_category_is_existed in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            categories = None
        return categories

    
    def check_subcategory_is_existed(self,category_id,subcategory):
        try:
            subcategories = WikiSubCategories.objects.filter(category_id=category_id,sub_category=subcategory).exists()
        except Exception as error:
            self.__log.error(
                f'Error in the method method check_subcategory_is_existed in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            subcategories = None
        return subcategories

    # statistics
    def get_pi_chart_data(self,start,end):
        try:
            query = """
                    select (select count(id) from wiki_pages 
                    where active=1 and created_at >= %s
                    and created_at <= %s
                    ) pages, (select count(id) from wiki_edited_pages  
                    where active=1 and created_at >= %s
                    and created_at <= %s
                    )edited,
                    (select count(id) from wiki_categories 
                    where active=1 and created_at >= %s
                    and created_at <= %s
                    ) category,
                    (select count(id) from wiki_page_likes 
                    where  created_at >= %s
                    and created_at <= %s
                    ) liked"""

            with connection.cursor() as cursor:
               cursor.execute(query,[str(start),str(end),str(start),str(end),str(start),str(end),str(start),str(end)])
               columns = [column[0] for column in cursor.description]
               result_list = []
               for row in cursor.fetchall():
                  result_list.append(dict(zip(columns, row)))
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_pi_chart_data in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            result_list = None
        return result_list


    def get_bar_chart_data(self,start,end):
        try:
            query="""
                select category,page,edited,liked from (
                select category,
                (select count(id) from wiki_pages where category_id = wc.id) page,
                (select count(id) from wiki_edited_pages where category_id = wc.id) edited,
                (select count(id) from wiki_page_likes where page_id = wp.id) liked
                from wiki_categories wc  
                left join wiki_pages wp on wc.id = wp.category_id 
                where  wc.created_at >= %s
                and wc.created_at <= %s)p where p.page >  0 or ( p.edited > 0 or liked > 0)
                group by category
            """
            with connection.cursor() as cursor:
               cursor.execute(query,[str(start),str(end)])
               columns = [column[0] for column in cursor.description]
               result_list = []
               for row in cursor.fetchall():
                  result_list.append(dict(zip(columns, row)))
        except Exception as error:
            self.__log.error(
                f'Error in the method method get_pi_chart_data in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            result_list = None
        return result_list


    def get_user_wise_report(self,start,end):
        try:
            query="""select CONCAT(au.first_name,' ',au.last_name) username,
                    (select count(id) from wiki_categories where created_by = au.id 
                    and (created_at >= %s and created_at <= %s)) category,
                    (select count(id) from wiki_pages where created_by = au.id 
                    and (created_at >= %s and created_at <= %s)) page,
                    (select count(id) from wiki_edited_pages where created_by = au.id 
                    and (created_at >= %s and created_at <= %s)) edited,
                    (select count(id) from wiki_page_likes where user_id= au.id 
                    and (created_at >= %s and created_at <= %s)) liked 
                    from auth_user au"""
            with connection.cursor() as cursor:
               cursor.execute(query,[str(start),str(end),str(start),str(end),
               str(start),str(end),str(start),str(end)])
               columns = [column[0] for column in cursor.description]
               result_list = []
               for row in cursor.fetchall():
                  result_list.append(dict(zip(columns, row)))

        except Exception as error:
            self.__log.error(
                f'Error in the method  get_user_wise_report in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            result_list = None
        return result_list

    def get_single_category_by_name(self,category):
        try:
            categories = WikiCategories.objects.get(category=category)
        except Exception as error:
            self.__log.error(
                f'Error in the method  get_single_category_by_name in AdminMasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            categories = None
        return categories

