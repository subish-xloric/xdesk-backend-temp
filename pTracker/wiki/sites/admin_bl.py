from types import SimpleNamespace
from django.template.loader import get_template
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from pTracker.wiki.common.forms.admin_forms import ApproveForm
from pTracker.wiki.data_access.replica.admin_master_da import AdminMasterDA
from pTracker.wiki.data_access.master.admin_master_da import AdminMasterData
from pTracker.wiki.data_access.replica.master_da import MasterDA
from pTracker.wiki.data_access.wiki_models.models import WikiCategories, WikiPageAttachments
from pTracker.wiki.sites.versioning_bl import Versioning_BL
from django.core.mail import EmailMessage
import os
import uuid
from pTracker.common.utility import Utility
from pTracker.wiki.data_access.master.logs_da import LogsDA
from django.utils import timezone
from django.utils import formats
from io import BytesIO
from xhtml2pdf import pisa
from openpyxl import Workbook
from datetime import datetime

class AdminBl():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.audit_logs = Utility().get_audit_logs_dict()


    def admin_all_page_list(self, request):
        try:
            if request.method == 'POST':
                try:
                    # Draw counter. Sent by the databale to identify ajax request order.
                    # We have return this in the response.
                    draw = int(request.POST.get('draw', 0))

                    # Pagination data. '0' will be first page.
                    start = int(request.POST.get('start', 0))

                    # Number of records to display. This is the limit value.
                    length = int(request.POST.get('length', 0))

                    # Value entered in the search input
                    search_string = request.POST.get('search[value]')

                    # Column index of the column on which sorting is to be done.
                    order_column = int(request.POST.get('order[0][column]', 0))

                    # Order type 'asc' or 'desc'
                    order_type = request.POST.get('order[0][dir]', 'asc')
                    order_type = False if order_type == 'asc' else True

                    articles = AdminMasterDA().get_all_pages_from_view(approver=request.user.id)
                    articles = articles.values('id','page_id','page_heading','category_id',
                                            'created_by','approved_by','status','remarks',
                                            'created_at','permalink','tbl')
                    records_total = articles.count()
                    records_filtered = records_total
                    if search_string:
                        articles = articles.filter(page_heading__icontains = search_string)
                        records_filtered = articles.count()
                    if request.POST.get('category'):
                        articles = articles.filter(category_id = request.POST.get('category'))
                        records_filtered = articles.count()
                    if request.POST.get('author'):
                        articles = articles.filter(created_by = request.POST.get('author'))
                        records_filtered = articles.count()
                    if request.POST.get('approved_by'):
                        articles = articles.filter(approved_by = request.POST.get('approved_by'))
                        records_filtered = articles.count()
                    if request.POST.get('status'):
                        articles = articles.filter(status = request.POST.get('status'))
                        records_filtered = articles.count()

                    # Applying pagination
                    articles = articles[start: (start + length)]
                    data_list = []
                    for cat in articles:
                        try:
                            category = MasterDA().get_category(category_id = cat.get('category_id'))
                            category = category.category
                        except Exception as error:
                            category = '----'
                        try:
                            author = MasterDA().get_author(user_id=cat.get('created_by'))
                            author = str(author.first_name) +' '+str(author.last_name)
                        except Exception as error:
                            author = '----'
                        try:
                            approver = MasterDA().get_author(user_id=cat.get('approved_by'))
                            approver = str(approver.first_name) +' '+str(approver.last_name)
                        except Exception as error:
                            approver = '----'

                        if cat.get('status') == 0:
                            status_label = '<span class="label label-warning">Pending</span>'
                        elif cat.get('status') == 1:
                            status_label = '<span class="label label-success">Approved</span>'
                        elif cat.get('status') == 2:
                            status_label = '<span class="label label-danger">Rejected</span>'

                        data = []

                        if cat.get('status') == 0 and cat.get('tbl') == 'submited':
                            action = f"""
                                     <a href="/wiki/admin/{cat.get('page_id')}/view-page/" class="btn btn-xs btn-info">View</a>
                                    """
                            action += f"""
                                    <a href="/wiki/admin/{cat.get('page_id')}/approve/" class="btn btn-xs btn-success">Approve</a>
                                    """
                            action += f"""
                                    <a onclick="return confirm('Are you sure want to delete?.')"
                                    href="/wiki/admin/remove-page/{cat.get('page_id')}" class="btn btn-danger btn-xs">Delete</a>"""

                        elif cat.get('status') == 1 and cat.get('tbl') == 'submited':
                            action = f"""<a href="/wiki/page-history/{cat.get('page_id')}/{cat.get('permalink')}"
                                    class="btn btn-primary btn-xs">history</a>
                                    """
                            action+=f"""
                                    <a onclick="return confirm('Are you sure want to delete?.')"
                                    href="/wiki/admin/remove-page/{cat.get('page_id')}" class="btn btn-danger btn-xs">Delete</a>
                                    """
                        elif cat.get('status') == 2 and cat.get('tbl') == 'submited':
                            action=f"""
                                    <a onclick="return confirm('Are you sure want to delete?.')"
                                    href="/wiki/admin/remove-page/{cat.get('page_id')}" class="btn btn-danger btn-xs">Delete</a>
                                    """
                        # edited table actions
                        if cat.get('status') == 0 and cat.get('tbl') == 'edited':
                            action = f"""
                                     <a href="/wiki/admin/4/{cat.get('page_id')}/compare-pages/" class="btn btn-primary btn-xs">Compare</a>
                                     """
                            action += f"""
                                     <a href="/wiki/admin/{cat.get('id')}/view-edited-page/" class="btn btn-info btn-xs">View</a>
                                     """
                            action += f"""
                                     <a href="/wiki/admin/{cat.get('id')}/approve-edited/" class="btn btn-xs btn-success">Approve</a>
                                     """
                            action += f"""
                                    <a onclick="return confirm('Are you sure want to delete?.')"
                                    href="/wiki/admin/remove-edited-page/{cat.get('id')}" class="btn btn-danger btn-xs">Delete</a>"""
                        elif cat.get('status') in [1,2] and cat.get('tbl') == 'edited':
                            action = f"""
                                    <a onclick="return confirm('Are you sure want to delete?.')"
                                    href="/wiki/admin/remove-edited-page/{cat.get('id')}" class="btn btn-danger btn-xs">Delete</a>"""
                        # title as article link
                        if cat.get('status') == 1 and cat.get('tbl') == 'submited':
                            heading = f"""
                                        <a href="/wiki/pages/article/{cat.get('page_id')}/{cat.get('permalink')}">{cat.get('page_heading')}</a>
                                     """
                        else:
                            heading = f"""{cat.get('page_heading')} <br><b class="text-danger">({cat.get('tbl')})</b>"""

                        data.append(heading)
                        data.append(category)
                        data.append(author)
                        data.append(approver)
                        data.append(status_label)
                        data.append(cat.get('remarks') if cat.get('remarks') else '----')
                        data.append(formats.date_format(cat.get('created_at'), "DATE_FORMAT"))
                        data.append(action)
                        data_list.append(data)
                    response = {
                        'draw': draw,
                        'recordsTotal': records_total,
                        'recordsFiltered': records_filtered,
                        'data': data_list
                    }
                except Exception as error:
                    response = {
                        'draw': 1,
                        'recordsTotal': 0,
                        'recordsFiltered': 0,
                        'data': []
                    }
                    print(error)
                return JsonResponse(response)
            categories = MasterDA().get_all_categories()
            author = AdminMasterDA().get_all_users()
            approvers = AdminMasterDA().get_all_approvers()
            variables = {'categories':categories,'author':author,'approvers':approvers}
            template = get_template('admin/all_articles.html')
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_all_page_list in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'categories':categories,'author':author,'approvers':approvers}
        return HttpResponse(template.render(variables, request))


    def admin_page_list(self, request):
        try:
            user_id = request.user.id
            pages = AdminMasterDA().get_all_pages_from_submitted(user_id)
            for page in pages:
                created_by = MasterDA().get_single_user(page.created_by)
                page.created_by = str(created_by.first_name) +' '+str(created_by.last_name)
                if page.status == 0:
                    page.status_label = '<span class="label label-warning">Pending</span>'
                elif page.status == 1:
                    page.status_label = '<span class="label label-success">Approved</span>'
                elif page.status == 2:
                    page.status_label = '<span class="label label-danger">Rejected</span>'

            page = request.GET.get('page')
            results_per_page = 1000 #to get more data for client side datatable
            paginator = Paginator(pages, results_per_page)
            try:
                pages = paginator.page(page)
            except PageNotAnInteger:
                pages = paginator.page(1)
            except EmptyPage:
                pages = paginator.page(paginator.num_pages)

            variables = {'pages': pages}
            template = get_template('admin/pages_list.html')
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_page_list in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'pages': pages}
        return HttpResponse(template.render(variables, request))


    def admin_edited_page_list(self, request):
        try:
            user_id = request.user.id
            pages = AdminMasterDA().get_all_pages_from_edited(user_id)
            for page in pages:
                created_by = MasterDA().get_single_user(page.created_by)
                page.created_by = str(created_by.first_name) +' '+str(created_by.last_name)
                if page.status == 0:
                    page.status_label = '<span class="label label-warning">Pending</span>'
                elif page.status == 1:
                    page.status_label = '<span class="label label-success">Approved</span>'
                elif page.status == 2:
                    page.status_label = '<span class="label label-danger">Rejected</span>'

            page = request.GET.get('page')
            results_per_page = 1000 #to get more data for client side datatable
            paginator = Paginator(pages, results_per_page)
            try:
                pages = paginator.page(page)
            except PageNotAnInteger:
                pages = paginator.page(1)
            except EmptyPage:
                pages = paginator.page(paginator.num_pages)

            variables = {'pages': pages}
            template = get_template('admin/edited_pages_list.html')
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_edited_page_list in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'pages': pages}
        return HttpResponse(template.render(variables, request))


    def admin_view_page(self, request, slug):
        try:
            page = AdminMasterDA().get_single_page(slug)
            attachment = MasterDA().get_page_attachements(slug)
            for x in attachment:
                att = str(x.attachments).split('/')
                x.attachments = att[3]
                x.path = f"{att[0]}/{att[1]}/{att[2]}"
            tags = list(page.tags.split(","))
            variables = {'article': page, 'tags': tags,
                         'attachments': attachment}
            template = get_template('admin/view_article.html')
        except Exception as error:
            self.__log.error(
                f'Error in the method  admin_view_page in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'article': page, 'tags': tags,
                         'attachments': attachment}
        return HttpResponse(template.render(variables, request))


    def admin_view_edited_page(self, request, slug):
        try:
            page = AdminMasterDA().get_single_edited_page(slug)
            variables = {'article': page}
            template = get_template('admin/view_edited_article.html')
        except Exception as error:
            self.__log.error(
                f'Error in the method  admin_view_edited_page in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'article': page}
        return HttpResponse(template.render(variables, request))


    def admin_compare_edited_page_with_page(self,request,page_id,page_id2):
        try:
            content_1 = MasterDA().get_single_page(page_id2)
            content_2 = AdminMasterDA().get_single_edited_page(page_id)
            html1,html2 = Versioning_BL().find_deffrence(content_1.page_content, content_2.page_content)

            if html1 and html2:
                content_1.page_content = str(html2)
                content_2.page_content = str(html1)

            template = get_template('admin/compare_history.html')
            variables = {'article':content_2,'content_1': content_1,'content_2':content_2}
        except Exception as error:
            self.__log.error(
                f'Error in the method  admin_view_edited_page in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'article':content_2,'content_1': content_1,'content_1':content_1}
        return HttpResponse(template.render(variables, request))


    def admin_change_page_status(self, request, slug):
        try:
            form = ApproveForm()
            page = AdminMasterDA().get_single_page(slug)
            if page.status:
                messages.error(
                    request, f'Article:{page.page_heading},You cannot change the status again')
                return redirect('page_list')
            created_by = page.created_by
            approver = page.approver
            approved_by = request.user.id
            if request.method == 'POST':
                form = ApproveForm(request.POST)
                if form.is_valid():
                    dto = SimpleNamespace()
                    dto.page_id = request.POST.get('page_id')
                    dto.approved_by = approved_by
                    dto.approved_at = timezone.now()
                    dto.status = request.POST.get('status')
                    dto.remarks = request.POST.get('remarks')
                    page_obj = AdminMasterData().update_page_status(data=dto)
                    if page_obj:
                        status = int(dto.status)
                        status = 'Approved' if status == 1 else 'Rejected'
                        approved_by = request.user
                        '''
                        self.send_mail_to_page_author(
                            page_obj, status, approved_by, created_by)
                        '''
                        if approver:
                            approved_by = request.user.id
                            if int(approver) != int(approved_by):
                                # send email to approver
                                approved_by = request.user
                                '''
                                self.send_mail_to_page_approver(
                                    page_obj, status, approver, approved_by, created_by)
                                '''
                        messages.success(
                            request, f'Article:{page.page_heading}, Status Updated Successfully!.')
                        #creating audit logs
                        self.audit_logs['user_id'] = request.user.id
                        self.audit_logs['event'] = 'Submited Page Status'
                        auditlog_details = f"""User with username {request.user}
                                            has updated status of page (id-{page.id})
                                            from pending to {status}'"""
                        self.audit_logs['event_details'] = str(auditlog_details)
                        LogsDA().create_audit_logs(self.audit_logs)
                        return redirect('page_list')
                    else:
                        messages.error(
                            request, f'Article:{page.page_heading}, Something went wrong while updating status!.')

            template = get_template('admin/approve_page.html')
            variables = {'article': page, 'form': form}
        except Exception as error:
            self.__log.error(
                f'Error in the method  admin_change_page_status in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'article': page, 'form': form}
        return HttpResponse(template.render(variables, request))


    def admin_change_edited_page_status(self,request,slug):
        try:
            form = ApproveForm()
            edited_page = AdminMasterDA().get_single_edited_page(slug)
            page = AdminMasterDA().get_single_page(edited_page.page_id)

            # if page.status:
            #     messages.error(
            #         request, f'Article:{page.page_heading},You cannot change the status again')
            #     return redirect('page_list')
            created_by = edited_page.created_by
            approver = edited_page.approver
            approved_by = request.user.id
            if request.method == 'POST':
                form = ApproveForm(request.POST)
                if form.is_valid():
                    dto = SimpleNamespace()
                    dto.page_id = slug
                    dto.approved_by = approved_by
                    dto.approved_at = timezone.now()
                    dto.status = request.POST.get('status')
                    dto.remarks = request.POST.get('remarks')
                    # comment
                    '''update_edited_page_status method has the logic of transferring
                     data from the edited table to main table then to the history table.'''
                    page_obj = AdminMasterData().update_edited_page_status(data=dto)
                    if page_obj:
                        status = int(dto.status)
                        status = 'Approved' if status == 1 else 'Rejected'
                        approved_by = request.user
                        '''
                        self.send_mail_to_page_author(
                            page, status, approved_by, created_by)
                        '''
                        if approver:
                            approved_by = request.user.id
                            if int(approver) != int(approved_by):
                                # send email to approver
                                approved_by = request.user
                                '''
                                self.send_mail_to_page_approver(
                                    page, status, approver, approved_by, created_by)
                                '''
                        messages.success(
                            request, f'Article:{page.page_heading}, Status Updated Successfully!.')
                        #creating audit logs
                        self.audit_logs['user_id'] = request.user.id
                        self.audit_logs['event'] = 'Edited Page Status'
                        auditlog_details = f"""User with username {request.user}
                                            has updated status of edited page (id-{slug})
                                            from pending to {status} page ({page.id})'"""
                        self.audit_logs['event_details'] = str(auditlog_details)
                        LogsDA().create_audit_logs(self.audit_logs)
                        return redirect('edited_page_list')
                    else:
                        messages.error(
                            request, f'Article:{page.page_heading}, Something went wrong while updating status!.')
            variables = {'article': page, 'form': form}
            template = get_template('admin/approve_edited_page.html')
        except Exception as error:
            self.__log.error(
                f'Error in the method  admin_edit_page in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'article': page, 'form': form}
        return HttpResponse(template.render(variables, request))


#send mails
    def send_mail_to_page_author(self, article, status, approved_by, created_by):
        try:
            created_by = MasterDA().get_single_user(created_by)
            context = {
                'article': article.page_heading,
                'status': status,
                'approver': str(approved_by.first_name)+' '+str(approved_by.last_name),
                'user': str(created_by.first_name)+' '+str(created_by.last_name),
                'designation': str(approved_by.groups.values_list('name', flat=True).first())
            }
            message = get_template(
                'email/article_status_to_author.html').render(context)
            msg = EmailMessage(
                f'{status} - {article.page_heading}',
                message,
                'wiki@digitalmesh.com',
                [created_by.email],
            )
            msg.content_subtype = "html"  # Main content is now text/html
            msg.send()
            print("Mail successfully sent")
        except Exception as error:
            self.__log.error(
                f'Error in the method  send_mail_to_page_author in AdminBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def send_mail_to_page_approver(self, article, status, approver, approved_by, created_by):
        try:
            created_by = MasterDA().get_single_user(created_by)
            approver = MasterDA().get_single_user(approver)
            context = {
                'article': article.page_heading,
                'status': status,
                'approver': str(approver.first_name)+' '+str(approver.last_name),
                'user': str(created_by.first_name)+' '+str(created_by.last_name),
                'approved_by': str(approved_by.first_name)+' '+str(approved_by.last_name),
                'designation': str(approved_by.groups.values_list('name', flat=True).first())
            }
            message = get_template(
                'email/article_status_to_approver.html').render(context)
            msg = EmailMessage(
                f'{status} - {article.page_heading}',
                message,
                'wiki@digitalmesh.com',
                [approver.email],
            )
            msg.content_subtype = "html"  # Main content is now text/html
            msg.send()
            print("Mail successfully sent")
        except Exception as error:
            self.__log.error(
                f'Error in the method  send_mail_to_page_approver in AdminBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def admin_page_categories_list(self,request):
        try:
            # categories = AdminMasterDA().get_all_page_categories()
            # page = request.GET.get('page')
            # results_per_page = 1000 #for client side datatable
            # paginator = Paginator(categories, results_per_page)
            # try:
            #     categories = paginator.page(page)
            # except PageNotAnInteger:
            #     categories = paginator.page(1)
            # except EmptyPage:
            #     categories = paginator.page(paginator.num_pages)

            variables = {}
            template = get_template('admin/categories_list.html')
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_page_list in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {}
        return HttpResponse(template.render(variables, request))


    def admin_page_categories_list_datatable(self,request):

        try:
            # Draw counter. Sent by the databale to identify ajax request order.
            # We have return this in the response.
            draw = int(request.POST.get('draw', 0))

            # Pagination data. '0' will be first page.
            start = int(request.POST.get('start', 0))

            # Number of records to display. This is the limit value.
            length = int(request.POST.get('length', 0))

            # Value entered in the search input
            search_string = request.POST.get('search[value]')

            # Column index of the column on which sorting is to be done.
            order_column = int(request.POST.get('order[0][column]', 0))

            # Order type 'asc' or 'desc'
            order_type = request.POST.get('order[0][dir]', 'asc')
            order_type = False if order_type == 'asc' else True

            categories = AdminMasterDA().get_all_page_categories()
            categories = categories.values('id','category')
            records_total = categories.count()
            if search_string:
                categories = categories.filter(category__icontains = search_string)
                records_filtered = categories.count()
            else:
                records_filtered = records_total
            # Applying pagination
            categories = categories[start: (start + length)]
            data_list = []
            for cat in categories:
                data = []
                action = f"""<a href="/wiki/admin/page/categories/{cat.get('id')}/edit/" class="btn btn-primary btn-xs">Edit</a>
                         <a onclick="return confirm('Are you sure want to delete?.')" href="/wiki/admin/page/categories/{cat.get('id')}/remove/" class="btn btn-danger btn-xs">Remove</a>
                         """
                data.append(cat.get('category'))
                data.append(action)
                data_list.append(data)
            response = {
                'draw': draw,
                'recordsTotal': records_total,
                'recordsFiltered': records_filtered,
                'data': data_list
            }
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_page_list_datatable in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            response = {
                'draw': 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            }
        return JsonResponse(response)


    def admin_add_page_categories(self,request):
        try:
            if request.method == 'POST':
                dto = SimpleNamespace()
                dto.category = request.POST.get('category')
                dto.category_description = request.POST.get('category_description')
                dto.active = request.POST.get('active')
                dto.created_by = request.user.id
                dto.sub_category = request.POST.getlist('sub_category[]')
                dto.sub_category_description = request.POST.getlist('sub_category_description[]')
                dto.sub_active = request.POST.getlist('sub_active[]')
                obj = AdminMasterData().create_categories(data=dto)
                if obj:
                    messages.success(request,'Category added successfully!.')
                    #creating audit logs
                    self.audit_logs['user_id'] = request.user.id
                    self.audit_logs['event'] = 'Add Category'
                    auditlog_details = f"""User with username {request.user}
                                        has added new category (id-{obj.id})"""
                    self.audit_logs['event_details'] = str(auditlog_details)
                    LogsDA().create_audit_logs(self.audit_logs)
                    return redirect('page_categories_list')
                else:
                    messages.error(request,'Something went wrong!..')
            template = get_template('admin/add_categories.html')
            variables = {}
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_add_page_categories in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {}
        return HttpResponse(template.render(variables, request))


    def admin_edit_page_categories(self,request,slug):
        try:
            if request.method == 'POST':
                dto = SimpleNamespace()
                dto.category_id = slug
                dto.category = request.POST.get('category')
                dto.category_description = request.POST.get('category_description')
                dto.active = request.POST.get('active')
                dto.created_by = request.user.id
                dto.sub_category_id = request.POST.getlist('sub_category_id[]')
                dto.sub_category = request.POST.getlist('sub_category[]')
                dto.sub_category_description = request.POST.getlist('sub_category_description[]')
                dto.sub_active = request.POST.getlist('sub_active[]')
                obj = AdminMasterData().update_categories(data=dto)
                if obj:
                    messages.success(request,'Category updated successfully!.')
                    #creating audit logs
                    self.audit_logs['user_id'] = request.user.id
                    self.audit_logs['event'] = 'Edit Category'
                    auditlog_details = f"""User with username {request.user}
                                        has edited category (id-{slug})"""
                    self.audit_logs['event_details'] = str(auditlog_details)
                    LogsDA().create_audit_logs(self.audit_logs)
                    return redirect('page_categories_list')
                else:
                    messages.error(request,'Something went wrong!..')
            category = AdminMasterDA().get_single_category(slug)
            sub_categories = AdminMasterDA().get_all_sub_categories(slug)
            template = get_template('admin/edit_categories.html')
            variables = {'category':category,'sub_categories':sub_categories}
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_edit_page_categories in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'category':category,'sub_categories':sub_categories}
        return HttpResponse(template.render(variables, request))


    def admin_remove_page_categories(self,request,slug):
        try:
            page = MasterDA().get_all_pages(category_id=slug,active=1)
            if not page:
                    obj = AdminMasterData().remove_category(slug)
                    if obj:
                        messages.success(request,'Category removed successfully!.')
                        #creating audit logs
                        self.audit_logs['user_id'] = request.user.id
                        self.audit_logs['event'] = 'Remove Category'
                        auditlog_details = f"""User with username {request.user}
                                            has removed category (id-{slug})"""
                        self.audit_logs['event_details'] = str(auditlog_details)
                        LogsDA().create_audit_logs(self.audit_logs)
                        return redirect('page_categories_list')
                    else:
                        messages.error(request,'Something went wrong!..')
                        return redirect('page_categories_list')
            else:
                messages.error(request,"Can't Delete, Article's Existed with this category.")
                return redirect('page_categories_list')
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_remove_page_categories in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def admin_remove_page_sub_category(self,request,slug):
        try:
            page = MasterDA().get_all_pages(sub_category_id=slug,active=1)
            if not page:
                obj = AdminMasterData().remove_sub_category(slug)
                if obj:
                    #creating audit logs
                    self.audit_logs['user_id'] = request.user.id
                    self.audit_logs['event'] = 'Remove sub Category'
                    auditlog_details = f"""User with username {request.user}
                                        has removed sub category (id-{slug})"""
                    self.audit_logs['event_details'] = str(auditlog_details)
                    LogsDA().create_audit_logs(self.audit_logs)
                    return HttpResponse(1)
                else:
                    return HttpResponse(0)
            else:
                return HttpResponse(2)
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_remove_page_sub_category in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def admin_remove_page(self,request,slug):
        try:
            obj = AdminMasterData().remove_page(slug)
            if obj:
                #creating audit logs
                self.audit_logs['user_id'] = request.user.id
                self.audit_logs['event'] = 'Remove page'
                auditlog_details = f"""User with username {request.user}
                                    has removed article (id-{slug})"""
                self.audit_logs['event_details'] = str(auditlog_details)
                LogsDA().create_audit_logs(self.audit_logs)
                messages.success(request,"Article Removed !")
            else:
                messages.error(request,"something went wrong !")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_remove_page_sub_category in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def admin_remove_edited_page(self,request,slug):
        try:
            obj = AdminMasterData().remove_edited_page(slug)
            if obj:
                #creating audit logs
                self.audit_logs['user_id'] = request.user.id
                self.audit_logs['event'] = 'Remove Edited page'
                auditlog_details = f"""User with username {request.user}
                                    has removed article (id-{slug})"""
                self.audit_logs['event_details'] = str(auditlog_details)
                LogsDA().create_audit_logs(self.audit_logs)
                messages.success(request,"Article Removed !")
            else:
                messages.error(request,"something went wrong !")
            return redirect('edited_page_list')
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_remove_page_sub_category in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def admin_check_category_is_existed(self,request):
        try:
            category = request.POST.get('category').strip()
            obj = AdminMasterDA().check_category_is_existed(category)
            if obj:
                return HttpResponse(1)
            else:
                return HttpResponse(0)
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_check_category_is_existed in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def admin_check_subcategory_is_existed(self,request):
        try:
            subcategory = request.POST.get('sub_category').strip()
            category = request.POST.get('category').strip()
            category_id = 0
            if category:
                category_raw = AdminMasterDA().get_single_category_by_name(category=category)
                if category_raw:
                    category_id = category_raw.id
            obj = AdminMasterDA().check_subcategory_is_existed(category_id, subcategory)
            if obj:
                return HttpResponse(1)
            else:
                return HttpResponse(0)
        except Exception as error:
            print(error)
            self.__log.error(
                f'Error in the  method admin_check_subcategory_is_existed in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def admin_view_statistics(self,request):
        try:
            if request.method == 'POST':
                start = request.POST.get('start_date')
                end = request.POST.get('end_date')
                type = request.POST.get('type')
                from_date = datetime.strptime(start,'%Y-%m-%d')
                from_date = datetime.strftime(from_date,'%d-%m-%Y')
                to_date = datetime.strptime(end,'%Y-%m-%d')
                to_date = datetime.strftime(to_date,'%d-%m-%Y')
                context = {}
                if type == 'pie':
                    pie_data = AdminMasterDA().get_pi_chart_data(start,end)
                    context = {
                        'from_date':from_date,
                        'to_date':to_date,
                        'data' : {
                        'labels': ["Article Submitted", "Article Edited", "Category", "Likes"],
                        'datasets': [{
                        'backgroundColor': [
                            "#2ecc71",
                            "red",
                            "orange",
                            "blue"
                        ],
                        'data': [pie_data[0]['pages'], pie_data[0]['edited'], pie_data[0]['category'], pie_data[0]['liked']]
                        }]
                        }
                        }

                elif type == 'bar':
                    bar_cahrt_data = AdminMasterDA().get_bar_chart_data(start,end)
                    # bar chart data
                    page_count = [x['page']for x in bar_cahrt_data]
                    edited_count = [x['edited']for x in bar_cahrt_data]
                    liked_count = [x['liked']for x in bar_cahrt_data]
                    context ={
                        'from_date':from_date,
                        'to_date':to_date,
                        'data' : {
                            'labels':[str(x['category']) for x in bar_cahrt_data],
                            'datasets':[{'label':'Article Submited','backgroundColor':'#2ecc71',
                            'data':page_count
                            },
                            {'label':'Article Edited','backgroundColor':'red',
                            'data':edited_count
                            },
                            {'label':'Likes','backgroundColor':'blue',
                            'data':liked_count
                            }]
                        }
                    }
                return JsonResponse(context)
            variables = {}
            template = get_template('admin/statistics.html')
        except Exception as error:
            self.__log.error(
                f'Error in the  method admin_view_statistics in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {}
        return HttpResponse(template.render(variables, request))


    def render_to_pdf(self,template_src, context_dict={}):
        try:
            template = get_template(template_src)
            html  = template.render(context_dict)
            result = BytesIO()
            #This part will create the pdf.
            pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
            if not pdf.err:
                return HttpResponse(result.getvalue(), content_type='application/pdf')
            return None
        except Exception as error:
            self.__log.error(
                f'Error in the method render_to_pdf in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def make_statistics_as_pdf(self,request):
        try:
            chart = request.POST.get('chart')
            variables = {'chart':chart}
            pdf = self.render_to_pdf('admin/render_to_pdf.html',variables)
            #rendering the template
            return HttpResponse(pdf, content_type='application/pdf')
        except Exception as error:
            self.__log.error(
                f'Error in the method make_statistics_as_pdf in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def make_user_wise_report(self,request):
        try:
            start = request.POST.get('from_date')
            end = request.POST.get('to_date')
            user_data = AdminMasterDA().get_user_wise_report(start,end)
            wb = Workbook()

            start = datetime.strptime(start,'%Y-%m-%d')
            start = datetime.strftime(start,'%d-%m-%Y')
            end = datetime.strptime(end,'%Y-%m-%d')
            end = datetime.strftime(end,'%d-%m-%Y')

            # grab the active worksheet
            ws = wb.active

            # Data can be assigned directly to cells
            ws.merge_cells('A1:E1')
            ws['A1'] = f"""User wise Report (From {start} To {end})"""

            ws['A3'] = 'User'
            ws['B3'] = 'Category'
            ws['C3'] = 'Page'
            ws['D3'] = 'Edited'
            ws['E3'] = 'Liked'

            # Rows can also be appended
            for data in user_data:
                 ws.append([data['username'],data['category'],data['page'], data['edited'], data['liked']])

            workbook_stream = BytesIO()
            wb.save(workbook_stream)
            workbook_stream.seek(0)
            response = HttpResponse(
                content=workbook_stream.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=wiki-user-wise-report{start}-{end}.xlsx'
            return response
        except Exception as error:
            self.__log.error(
                f'Error in the method make_user_wise_report in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
