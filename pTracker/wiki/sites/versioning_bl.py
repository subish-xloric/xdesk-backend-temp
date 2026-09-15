from django.utils import html
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from django.template.loader import get_template
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.contrib import messages
from pTracker.wiki.data_access.replica.master_da import MasterDA
from pTracker.wiki.data_access.replica.versioning_da import Versioning_DA
import os
from django.utils.html import strip_tags
from bs4 import BeautifulSoup
import uuid


class Versioning_BL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()


    def page_history(self, request, slug):
        try:
            article = MasterDA().get_single_page(slug)
            page_history = Versioning_DA().get_page_history(slug)
            template=get_template('versioning/page_history.html')
            variables = {'article':article,'page_history':page_history}
        except Exception as error:
            self.__log.error(
                f'Error in the method page_history in VersioningBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'article':article,'page_history':page_history}
        return HttpResponse(template.render(variables,request))


    def view_page_source_history(self, request, type, slug):
        try:
            article = {}
            if type == 'M':
                article = MasterDA().get_single_page(slug)
            else:
                article = Versioning_DA().get_single_page_history(slug)
            template=get_template('versioning/view_source_history.html')
            variables = {'article':article}
        except Exception as error:
            self.__log.error(
                f'Error in the method view_page_source_history in VersioningBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'article':article}
        return HttpResponse(template.render(variables,request))

    # def compare_page_history(self,request):
    #     try:
    #         version = request.POST.get('version').split('_')
    #         diffver = request.POST.get('diffver').split('_')
    #         version_type = str(version[0])
    #         version_id = int(version[1])
    #         diffver_type = str(diffver[0])
    #         diffver_id = int(diffver[1])

    #         if version_type == 'H' and diffver_type == 'M':
    #             content_1 = MasterDA().get_single_page(diffver_id)
    #             content_2 = Versioning_DA().get_single_page_history(version_id)
    #         else:
    #             content_1 = Versioning_DA().get_single_page_history(diffver_id)
    #             content_2 = Versioning_DA().get_single_page_history(version_id)
    #         # writing page contents in a txt file in oredre to compare line by line
    #         with open(os.path.join(settings.MEDIA_ROOT, 'versioning/content_1.txt'), 'w') as f:
    #                 f.write(strip_tags(content_1.page_content))
    #         with open(os.path.join(settings.MEDIA_ROOT, 'versioning/content_2.txt'), 'w') as f:
    #                 f.write(strip_tags(content_2.page_content))
    #         #comparing the txt files and return the diffrence
    #         file_1 = set()
    #         file_2 = set()

    #         with open(os.path.join(settings.MEDIA_ROOT, 'versioning/content_1.txt'), 'r') as f:
    #             for line in f:
    #                 file_1.add(line.strip())

    #         with open(os.path.join(settings.MEDIA_ROOT, 'versioning/content_2.txt'), 'r') as f:
    #             for line in f:
    #                 file_2.add(line.strip())

    #         file1 = file_1 - file_2
    #         file2 = file_2 - file_1
    #         print(file1)
    #         #replace content in content_1.page_content object
    #         for rep in file1:
    #             content_1.page_content = content_1.page_content.replace(rep,f'<span class="bg-success">{rep}</span>')
    #         #replace content in content_1.page_content object
    #         for rep in file2:
    #             content_2.page_content = content_2.page_content.replace(rep,f'<span class="bg-danger">{rep}</span>')
    #         #remove files created for comparison
    #         # if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'versioning/content_2.txt')):
    #         #     os.remove(os.path.join(settings.MEDIA_ROOT, 'versioning/content_2.txt'))
    #         # if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'versioning/content_1.txt')):
    #         #     os.remove(os.path.join(settings.MEDIA_ROOT, 'versioning/content_1.txt'))
    #         template=get_template('versioning/compare_history.html')
    #         variables = {'version_type':diffver_type,'content_1':content_1,'content_2':content_2}
    #     except Exception as error:
    #         self.__log.error(
    #             f'Error in the method compare_page_history in VersioningBL., Error: {str(error)},'
    #             f'Error traceback: {self.__exception.exception()}'
    #         )
    #         variables = {'version_type':diffver_type,'content_1':content_1,'content_2':content_2}
    #     return HttpResponse(template.render(variables,request))


    def compare_page_history(self,request):
        try:
            version = request.POST.get('version').split('_')
            diffver = request.POST.get('diffver').split('_')
            version_type = str(version[0])
            version_id = int(version[1])
            diffver_type = str(diffver[0])
            diffver_id = int(diffver[1])

            if version_type == 'H' and diffver_type == 'M':
                content_1 = MasterDA().get_single_page(diffver_id)
                content_2 = Versioning_DA().get_single_page_history(version_id)
            else:
                content_1 = Versioning_DA().get_single_page_history(diffver_id)
                content_2 = Versioning_DA().get_single_page_history(version_id)
            # Get the page contents directly
            html1,html2 = self.find_deffrence(content_1.page_content, content_2.page_content)

            if html1 and html2:
                content_1.page_content = str(html2)
                content_2.page_content = str(html1)

            template=get_template('versioning/compare_history.html')
            variables = {'version_type':diffver_type,'content_1':content_1,'content_2':content_2}
        except Exception as error:
            self.__log.error(
                f'Error in the method compare_page_history in VersioningBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'version_type':diffver_type,'content_1':content_1,'content_2':content_2}
        return HttpResponse(template.render(variables,request))


    def find_deffrence(self, content_1, content_2):
            first_file_lines = content_1.splitlines(keepends=True) if content_1 else []
            second_file_lines = content_2.splitlines(keepends=True) if content_2 else []
            
            diffrence = self.create_diffrence(second_file_lines,first_file_lines,"","")
            file = diffrence.replace('&nbsp;',' ')
            del diffrence
            # print(diffrence)
            soup = BeautifulSoup(file,'html.parser')
            table = soup.find('table',attrs={'class':'diff'}).tbody
            table = str(table).replace('<tbody>','<table>')
            table = str(table).replace('</tbody>','</table>')
            soup1 = BeautifulSoup(str(table),'html.parser')
            # print(len(soup.find_all('tr')))
            html1 = ""
            tr_length = len(soup1.find_all('tr'))+1

            #extracting row id from td 
            element_class = soup1.find('td',attrs={'class':'diff_next'})
            row_number = element_class.get('id')
            if row_number:
                row_number =row_number.split('to')
                row_number = row_number[1].split('__')
                row_number = row_number[0]
            else:
                row_number = element_class.find('a')
                row_number = row_number.get('href').split("to")
                row_number = row_number[1].split('__')
                row_number = row_number[0]
                # print(row_number)
            row_number = row_number
            for x in range(tr_length):
                if x != 0:
                    id = f'from{row_number}_{x}'
                    for element in soup1.find_all('td',attrs={'id':id}):
                        html1 += str(element.findNext('td'))

            html1 = str(html1).replace('<td nowrap="nowrap">','<div>').replace('</td>','</div>')
            html2 = ""
            for x in range(tr_length):
                if x != 0:
                    id = f'to{row_number}_{x}'
                    for element in soup1.find_all('td',attrs={'id':id}):
                        html2 += str(element.findNext('td'))
            del soup1
            html2 = str(html2).replace('<td nowrap="nowrap">','<div>').replace('</td>','</div>')
            
            return html1,html2


    def create_diffrence(self,second_file_lines,first_file_lines,second_file,first_file):
        import difflib
        return difflib.HtmlDiff().make_file(second_file_lines,first_file_lines,second_file,first_file)