from django.db.models import Q
from django.db.models import Count, Max
from django.db.models import query
from django.db.models.query import QuerySet
from pTracker.wiki.data_access.wiki_models.models import WikiPageHistory, WikiSubCategories,WikiCategories
from pTracker.wiki.data_access.wiki_models.models import WikiPages, WikiEditedPages
from pTracker.wiki.data_access.wiki_models.models import WikiPageLikes
from pTracker.wiki.data_access.wiki_models.models import WikiPopularTags
from pTracker.wiki.data_access.wiki_models.models import WikiPageAttachments
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from django.contrib.auth.models import User
from django.db import connection


class MasterDA():
      def __init__(self):
         self.__log = Logs()
         self.__exception = ExceptionHandler()

      def get_users_username(self,email=None):
         try:
            username = User.objects.filter(email = email).first().username
         except Exception as error:
            self.__log.error(
               f'Error in the method method get_users_username in MasterDA(replica)., Error: {str(error)},'
               f'Error traceback: {self.__exception.exception()}'
            )
            username = None
         return username


      def get_author(self, user_id):
         try:
            author = User.objects.get(id = user_id)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_author in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            author = None
         return author


      def get_single_user(self, user_id):
         try:
            user = User.objects.get(id = user_id)
         except Exception as error:
            self.__log.error(
                f'Error in the method  get_single_user in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            user = None
         return user


      def get_category(self, category_id):
         try:
            category = WikiCategories.objects.filter(id = category_id,active=1).first()
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_category in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            category = None
         return category


      def get_all_categories(self,limit=None):
         try:
            if limit:
               category = (WikiCategories.objects
                                 .filter(active=1)
                                 .annotate(dcount=Count('wikipages'))
                                 .annotate(last_page_created=Max('wikipages__id'))
                                 .order_by('-wikipages__id')[:limit])
            else:
               category = (WikiCategories.objects
                              .filter(active=1)
                              .annotate(dcount=Count('wikipages'))
                              .annotate(last_page_created=Max('wikipages__id'))
                              .order_by('-wikipages__id'))
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_all_categories in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            category = None
         return category


      def get_sub_categories(self, category_id):
         try:
            subcategory = WikiSubCategories.objects.filter(category_id = category_id,active=1).order_by('sub_category')
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_sub_categories in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            subcategory = None
         return subcategory


      def get_all_pages(self, **kwargs):
         try:
            if kwargs:
               pages = WikiPages.objects.filter(**kwargs)
            else:
               pages = WikiPages.objects.filter(status=1)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_all_pages in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            pages = None
         return pages


      def get_searh_pages(self,search):
         try:
            pages = WikiPages.objects.filter(
                      Q(page_heading__icontains=search)
                     |Q(page_content__icontains=search)
                     |Q(tags__icontains=search),active=1,status=1).order_by('-page_heading')
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_searh_pages in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            pages = None
         return pages


      def get_single_page(self, slug , status = [1]):
         try:
            page = WikiPages.objects.get(id=slug,status__in=status,active=1)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_single_page in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page = None
         return page


      def get_page_attachements(self, slug):
         try:
            attachments = WikiPageAttachments.objects.filter(page_id=slug)
         except Exception as error:
            self.__log.error(
                f'Error in the method  get_page_attachements in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            attachments = None
         return attachments


      def get_edited_page(self, slug, user_id):
         try:
            page = WikiEditedPages.objects.get(page_id=slug, created_by=user_id)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_edited_page in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page = None
         return page


      def get_user_page_like(self, user_id, page_id):
         try:
            page_like = WikiPageLikes.objects.get(user_id=user_id, page_id=page_id)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_user_page_like in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            page_like = None
         return page_like


      def get_popular_articles(self):
         try:
            query = '''select wpl.id,wp.page_heading,wp.permalink ,page_id,
                              COUNT(is_liked)count from wiki_page_likes wpl
                              join wiki_pages wp on wpl.page_id = wp.id
                              where wpl.is_liked = 1 and wp.status = 1 and wp.active = 1
                              group by page_id
                              order by COUNT(is_liked) desc limit 20'''
            popular_article = WikiPageLikes.objects.raw(query)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_popular_articles in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            popular_article = None
         return popular_article


      def get_latest_articles(self):
         try:
            latest_article = WikiPages.objects.filter(status=1,active=1).order_by('-created_at')[:10]
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_latest_articles in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            latest_article = None
         return latest_article


      def get_popular_tags(self):
         try:
            popular_tags = WikiPopularTags.objects.values('tag').order_by('-clicked')[:30]
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_popular_tags in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            popular_tags = None
         return popular_tags


      def get_my_articles(self,user_id,search=None):
         try:
            query = """select wp.id id,wp.page_heading,wp.created_at,wp.status,wp.remarks,'Submited' tabl
                     from wiki_pages wp where created_by = %s and wp.active=1
                     union
                     select wep.page_id id,wp2.page_heading,wep.created_at,wep.status,wep.remarks,'Edited' tabl from wiki_edited_pages wep
                     join wiki_pages wp2 on wep.page_id=wp2.id 
                     where wep.created_by = %s and wep.active=1 and wp2.active =1
                     order by created_at desc"""

            with connection.cursor() as cursor:
               cursor.execute(query,[user_id,user_id])
               columns = [column[0] for column in cursor.description]
               result_list = []
               for row in cursor.fetchall():
                  result_list.append(dict(zip(columns, row)))
            # data_list = []
            # for data in result_list:
            #        if data['tabl'] =='edited' and data['status'] == 1:
            #             data_list.append(data)
            #        else:
            #             data_list.append(data)
            # print(result_list.query)
            # row = WikiPages.objects.filter(created_by = user_id).values('id','page_heading','created_at','status','remarks')
            # row1 = WikiEditedPages.objects.filter(created_by = user_id).values('page_id','page__page_heading','created_at','status','remarks')
            # # row2 = WikiPageHistory.objects.filter(created_by = user_id).values('page_heading','created_at','status','remarks')
            # result_list = row.union(row1).order_by('-created_at')
            # print(result_list.query)
            # result_list = result_list.union(row2, all=True).order_by('-created_at')

         except Exception as error:
            self.__log.error(
                f'Error in the method  get_my_articles in MasterDA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            result_list = None
         return result_list