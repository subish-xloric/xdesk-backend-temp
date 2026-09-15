from django.db.models import Q
from django.db.models import Count
from django.db.models import query
from pTracker.wiki.data_access.wiki_models.models import WikiPages
from pTracker.wiki.data_access.wiki_models.models import WikiPageHistory
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from django.db import connection


class Versioning_DA():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
    

    def  get_page_history(self,page_id):
        try:
            with connection.cursor() as cursor:
                query = """select '0' id,wp.id as page_id,au.first_name ,created_at,last_updated_at,'M' type from wiki_pages wp 
                            join auth_user au on wp.last_updated_by = au.id
                            where wp.id= %s and status=1 and active=1
                            union 
                            select wph.id, page_id,au.first_name ,created_at,last_updated_at,'H' type from wiki_page_history wph
                            join auth_user au on wph.last_updated_by = au.id
                            where page_id= %s and status=1 order by last_updated_at desc"""
                cursor.execute(query,[page_id,page_id])
                columns = [column[0] for column in cursor.description]
                result_list = []
                for row in cursor.fetchall():
                    result_list.append(dict(zip(columns, row)))
        except Exception as error:
            self.__log.error(
                f'Error in the method get_page_history in Versioning_DA., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            result_list = None
        return result_list

    
    def get_single_page_history(self, page_id):
         try:
            history = WikiPageHistory.objects.get(id=page_id,status=1)
         except Exception as error:
            self.__log.error(
                f'Error in the method method get_single_page_history in Versioning_DA(replica)., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            history = None
         return history



