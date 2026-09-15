from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.contrib import messages
from pTracker.wiki.data_access.replica.master_da import MasterDA
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler


class HomeBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()


    def home(self,request):
        try:
            categories = MasterDA().get_all_categories(limit=10)
            categories = [{'id':cate.id,'category': cate.category, 
                         'pages': [{'id': page.id, 'page_heading':page.page_heading,
                         'permalink':page.permalink,'created_at':page.last_updated_at} 
                         for page in cate.wikipages_set.filter(active=1,status=1)]}
                         for cate in categories]
            variables = {'categories':categories}
            template=get_template('index.html') 
        except Exception as error:
            self.__log.error(
                f'Error in the method method home in HomeBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'categories':None}
        return HttpResponse(template.render(variables,request))