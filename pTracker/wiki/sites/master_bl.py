from types import SimpleNamespace
from django.template.loader import get_template ,render_to_string
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from pTracker.wiki.utils.logs import Logs
from pTracker.wiki.utils.exception import ExceptionHandler
from pTracker.wiki.common.forms.maser_form import AddPageForm, EditPageForm
from pTracker.wiki.data_access.replica.master_da import MasterDA
from pTracker.wiki.data_access.master.master_da import MasterData
from pTracker.wiki.data_access.wiki_models.models import WikiPageAttachments
from django.core.mail import EmailMessage
from pTracker.common.utility import Utility
from pTracker.wiki.data_access.master.logs_da import LogsDA
from io import BytesIO
from xhtml2pdf import pisa
from django.utils import timezone

class MasterBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.audit_logs = Utility().get_audit_logs_dict()

    def my_articles(self,request):
        try:
            my_articles = MasterDA().get_my_articles(request.user.id)
            for article in my_articles:
                # print(article['status'])
                if article['status'] == 0:
                     article['status_label'] = f'<span class="label label-warning">Pending</span>'
                elif article['status'] == 1:
                     article['status_label'] = '<span class="label label-success">Approved</span>'
                elif article['status'] == 2:
                     article['status_label'] = '<span class="label label-danger">Rejected</span>'
            template = get_template('pages/my_articles.html')
            variables = {'my_articles':my_articles}
        except Exception as error:
            self.__log.error(
                f'Error in the method  my_articles in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'my_articles':my_articles}
        return HttpResponse(template.render(variables, request))


    def my_articles_datatable(self,request):
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

            my_articles = MasterDA().get_my_articles(request.user.id)
            records_total = my_articles.count()
            if search_string:
                my_articles = my_articles = MasterDA().get_my_articles(request.user.id,search_string)
                records_filtered = my_articles.query
            else:
                records_filtered = records_total
            # Applying pagination
            my_articles = my_articles[start: (start + length)]
            data_list = []
            for article in my_articles:
                data = []
                if article['status'] == 0:
                     article['status_label'] = '<span class="label label-warning">Pending</span>'
                elif article['status'] == 1:
                     article['status_label'] = '<span class="label label-success">Approved</span>'
                elif article['status'] == 2:
                     article['status_label'] = '<span class="label label-danger">Rejected</span>'
                data.append(article['page_heading'])
                data.append(article['created_at'])
                data.append(article['status_label'])
                data_list.append(data)
            response = {
                'draw': draw,
                'recordsTotal': records_total,
                'recordsFiltered': records_filtered,
                'data': data_list
            }
        except Exception as error:
            self.__log.error(
                f'Error in the  method my_articles_datatable in AdminBl., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            response = {
                'draw': 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            }
        return JsonResponse(response)


    def add_page(self, request):
        try:
            # checking user group
            user_group_id = int(request.user.groups.values_list('id', flat=True).first())
            form = AddPageForm()
            variables = {'form': form}
            template = get_template('pages/add_page.html')
            if request.method == 'POST':
                form = AddPageForm(request.POST)
                if form.is_valid():
                    files = request.FILES
                    dto = SimpleNamespace()
                    dto.page_heading = request.POST.get('page_heading')
                    dto.category = request.POST.get('category')
                    dto.sub_category = request.POST.get('sub_category') if request.POST.get('sub_category') else 0
                    dto.page_content = request.POST.get('page_content')
                    dto.short_description = request.POST.get('short_description')
                    dto.tags = request.POST.get('tags')
                    dto.approver = request.POST.get('approver')
                    dto.is_confidential = 1  # request.POST.get('is_confidential') if request.POST.get('is_confidential') else 0
                    dto.created_by = request.user.id
                    if user_group_id !=5:
                        dto.status = 1
                        dto.approved_by = request.user.id
                        dto.approved_at = timezone.now()
                    else:
                        dto.status = 0
                        dto.approved_by  = 0
                        dto.approved_at = timezone.now()
                    page_obj = MasterData().create_page(data=dto, files=files)
                    if page_obj:
                         # send email to approver
                        '''
                        if user_group_id == 5:
                            # send email notification to the selected approver
                            email = self.send_email_to_approver(page_obj.approver, request.user)
                        '''
                        messages.success(
                            request, 'The page has been submited successfully!. Waiting for approval')
                        #creating audit logs
                        self.audit_logs['user_id'] = request.user.id
                        self.audit_logs['event'] = 'Page Added'
                        auditlog_details = f"""User with username {request.user}
                                           has added an article (id-{page_obj.id})-'{page_obj.page_heading}'"""
                        self.audit_logs['event_details'] = str(auditlog_details)
                        LogsDA().create_audit_logs(self.audit_logs)
                        return redirect('add_page')
                    else:
                        messages.error(request, 'Something went wrong!.')
                else:
                    messages.error(request, 'Please fill all the mandatory fields!.')
                    variables = {'form': form}
        except Exception as error:
            self.__log.error(
                f'Error in the method method add_page in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'form': form}
        return HttpResponse(template.render(variables, request))


    def send_email_to_approver(self, approver, created_by):
        try:
            approver_obj = MasterDA().get_single_user(approver)
            context = {
                'approver': str(approver_obj.first_name)+' '+str(approver_obj.last_name),
                'user': str(created_by.first_name)+' '+str(created_by.last_name),
                'designation': str(created_by.groups.values_list('name', flat=True).first())
            }
            message = get_template('email/approver.html').render(context)
            msg = EmailMessage(
                'Pending Approval',
                 message,
                'wiki@mydomain.com',
                [approver_obj.email],
            )
            msg.content_subtype = "html"  # Main content is now text/html
            msg.send()
            print("Mail successfully sent")
        except Exception as error:
            self.__log.error(
                f'Error in the method method articles in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def edit_page(self, request, slug):
        try:
             # checking user group
            user_group_id = int(request.user.groups.values_list('id', flat=True).first())
            user_id = request.user.id
            article = MasterDA().get_edited_page(slug, user_id)
            if article:
                data_from = 'wiki_edited_pages'
                article_status = None
                article = {
                    'id': article.page_id,
                    'category_id': article.category_id,
                    'sub_category_id':article.sub_category_id,
                    'tags':article.tags,
                    'page_content': article.page_content,
                    'page_heading': article.page.page_heading,
                    'permalink': article.page.permalink,
                    'short_description': article.short_description,
                    'status':article.page.status,
                    'is_confidential':article.is_confidential
                }
            else:
                data_from = 'wiki_pages'
                status = [0,1,2]
                article = MasterDA().get_single_page(slug,status)
                article_status = article.status
            if request.method == 'POST':
                form = EditPageForm(request.POST)
                if form.is_valid():
                    dto = SimpleNamespace()
                    dto.page_id = int(request.POST.get('page_id'))
                    dto.category_id = int(request.POST.get('category'))
                    dto.sub_category_id = request.POST.get('sub_category') if request.POST.get('sub_category') else 0
                    dto.page_content = request.POST.get('page_content')
                    dto.tags = request.POST.get('tags')
                    dto.short_description = request.POST.get('short_description')
                    dto.approver = request.POST.get('approver')
                    dto.created_by = request.user.id
                    dto.is_confidential = 1 #request.POST.get('is_confidential') if request.POST.get('is_confidential') else 0
                    dto.status = 0
                    if user_group_id != 5:
                        dto.status = 1
                        dto.approved_by = request.user.id
                        dto.approved_at = timezone.now()
                    else:
                        dto.status = 0
                        dto.approved_by  = 0
                        dto.approved_at = timezone.now()
                    page_obj = MasterData().create_edited_page(data=dto,data_from=data_from,article_status=article_status)
                    if page_obj:
                         # send email to approver
                        '''
                        if user_group_id == 5:
                            # send email notification to the selected approver
                            email = self.send_email_to_approver(dto.approver, request.user)
                        '''
                        messages.success(
                            request, 'Page Changes has been submited successfully!. Waiting for approval')

                        #creating audit logs
                        try:
                            self.audit_logs['user_id'] = request.user.id
                            self.audit_logs['event'] = 'Page Edited'
                            auditlog_details = f"""User with username {request.user}
                                            has edited an article (id-{page_obj.page_id})-'{page_obj.page.page_heading}'"""
                            self.audit_logs['event_details'] = str(auditlog_details)
                        except:
                            self.audit_logs['user_id'] = request.user.id
                            self.audit_logs['event'] = 'Page Edited'
                            auditlog_details = f"""User with username {request.user}
                                            has edited an article (id-{page_obj.id})-'{page_obj.page_heading}'"""
                            self.audit_logs['event_details'] = str(auditlog_details)
                        LogsDA().create_audit_logs(self.audit_logs)
                        return redirect('edit_page', slug=dto.page_id)
                    else:
                        messages.error(request, 'Something went wrong!.')
            else:
                try:
                    initial_dict = {"category" : article.get('category_id')}
                except:
                    initial_dict = {"category" : article.category_id}
                form = EditPageForm(initial=initial_dict)

            variables = {'form': form, 'article': article}
            template = get_template('pages/edit_page.html')
        except Exception as error:
            self.__log.error(
                f'Error in the method method edit_page in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'form': form, 'article': article}
        return HttpResponse(template.render(variables, request))


    def manage_attachments(self,request,slug):
        try:
            attachments = MasterDA().get_page_attachements(slug)
            for x in attachments:
                att = str(x.attachments).split('/')
                x.attachments = att[3]
                x.path = f"{att[0]}/{att[1]}/{att[2]}"
            article = MasterDA().get_single_page(slug)
            template = get_template('pages/manage_attachments.html')
            page = request.GET.get('page')
            results_per_page = 20
            paginator = Paginator(attachments, results_per_page)

            try:
                attachments = paginator.page(page)
            except PageNotAnInteger:
                attachments = paginator.page(1)
            except EmptyPage:
                attachments = paginator.page(paginator.num_pages)

            if request.method == 'POST':
                files = request.FILES
                dto = SimpleNamespace()
                dto.created_by = request.user.id
                dto.page_id = request.POST.get('page_id')
                obj = MasterData().create_attachments(data=dto, files=files)
                if obj:
                    messages.success(request, 'Attachements Successfully added!.')
                    #creating audit logs
                    self.audit_logs['user_id'] = request.user.id
                    self.audit_logs['event'] = 'Manage Attachments'
                    auditlog_details = f"""User with username {request.user}
                                        has added attachments in page (id-{article.id})-'{article.page_heading}'"""
                    self.audit_logs['event_details'] = str(auditlog_details)
                    LogsDA().create_audit_logs(self.audit_logs)
                    return redirect('manage_attachments',slug=slug)
                else:
                    messages.error(request, 'Something went wrong !..')

            variables = {'attachments': attachments,'article':article}
        except Exception as error:
            self.__log.error(
                f'Error in the method method articles in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'attachments': attachments,'article':article}
        return HttpResponse(template.render(variables, request))


    def remove_attachments(self,request,slug,page_id):
        try:
            obj = MasterData().delete_attahcments(slug)
            if obj:
                messages.success(request, 'Attachement Removed Successfully!.')
                #creating audit logs
                self.audit_logs['user_id'] = request.user.id
                self.audit_logs['event'] = 'Remove Attachments'
                auditlog_details = f"""User with username {request.user}
                                    has removed attachment (id-{slug}) from page (id-{page_id})'"""
                self.audit_logs['event_details'] = str(auditlog_details)
                LogsDA().create_audit_logs(self.audit_logs)
                return redirect('manage_attachments',slug=page_id)
            else:
                messages.error(request, 'Something went wrong while removing attachment!..')
                return redirect('manage_attachments',slug=page_id)
        except Exception as error:
            self.__log.error(
                    f'Error in the method method articles in MasterBL., Error: {str(error)},'
                    f'Error traceback: {self.__exception.exception()}'
                )
            return redirect('manage_attachments',slug=page_id)


    def articles(self, request):
        try:
            pages = MasterDA().get_all_pages(active=1, status=1)
            template = get_template('pages/articles.html')
            page = request.GET.get('page')
            results_per_page = 10
            paginator = Paginator(pages, results_per_page)
            try:
                pages = paginator.page(page)
            except PageNotAnInteger:
                pages = paginator.page(1)
            except EmptyPage:
                pages = paginator.page(paginator.num_pages)

            variables = {'pages': pages}
        except Exception as error:
            self.__log.error(
                f'Error in the method method articles in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'pages': pages}
        return HttpResponse(template.render(variables, request))


    def article(self, request, slug, permalink):
        try:
            article = MasterDA().get_single_page(slug)
            user_id = request.user.id
            page_like = MasterDA().get_user_page_like(user_id=user_id, page_id=slug)
            attachment = MasterDA().get_page_attachements(slug)
            for x in attachment:
                att = str(x.attachments).split('/')
                x.attachments = att[3]
                x.path = f"{att[0]}/{att[1]}/{att[2]}"

            tags = list(article.tags.split(","))
            variables = {'article': article, 'tags': tags,
                         'page_like': page_like, 'attachments': attachment}
            template = get_template('pages/article.html')
        except Exception as error:
            print(error)
            self.__log.error(
                f'Error in the method method article in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'article': article, 'tags': tags,
                         'page_like': page_like, 'attachments': attachment}
        return HttpResponse(template.render(variables, request))


    def article_render_to_pdf(self,template_src, context_dict={}):
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
                f'Error in the method article_render_to_pdf in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def make_article_as_pdf(self,request,slug):
        try:
            article = MasterDA().get_single_page(slug)
            variables = {'article':article}
            pdf = self.article_render_to_pdf('pages/render_to_pdf.html',variables)
            #rendering the template
            return HttpResponse(pdf, content_type='application/pdf')
        except Exception as error:
            self.__log.error(
                f'Error in the method make_article_as_pdf in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )


    def page_category_wise(self, request, slug):
        try:
            category = MasterDA().get_category(category_id=slug)
            sub_category = MasterDA().get_sub_categories(category_id=slug)
            pages = MasterDA().get_all_pages(category_id=slug, status=1, active=1)
            page_count = pages.count()
            # getting sub categories
            if request.method == "POST":
                sub_category_id = request.POST.get('sub_category')
                pages = MasterDA().get_all_pages(category_id=slug,sub_category_id=sub_category_id, status=1, active=1)
                page_count = pages.count()
                page = request.POST.get('page')
                results_per_page = 10
                paginator = Paginator(pages, results_per_page)
                try:
                    pages = paginator.page(page)
                except PageNotAnInteger:
                    pages = paginator.page(1)
                except EmptyPage:
                    pages = paginator.page(paginator.num_pages)
                html = render_to_string(request=request,
                        template_name='common/article_box.html',
                        context={'pages': pages, 'page_count': page_count})
                return HttpResponse(html)

            page = request.GET.get('page')
            results_per_page = 10
            paginator = Paginator(pages, results_per_page)
            try:
                pages = paginator.page(page)
            except PageNotAnInteger:
                pages = paginator.page(1)
            except EmptyPage:
                pages = paginator.page(paginator.num_pages)

            variables = {'pages': pages, 'category': category,
                         'page_count': page_count,'sub_category':sub_category}
            template = get_template('pages/page_category_wise.html')
        except Exception as error:
            self.__log.error(
                f'Error in the method method page_category_wise in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'pages': '', 'category': category,
                         'page_count': page_count,'sub_category':sub_category}
        return HttpResponse(template.render(variables, request))


    def page_author_wise(self, request, slug):
        try:
            author = MasterDA().get_author(slug)
            pages = MasterDA().get_all_pages(created_by=slug, status=1, active=1)
            page_count = pages.count()
            template = get_template('pages/author_wise_articles.html')
            page = request.GET.get('page')
            results_per_page = 10
            paginator = Paginator(pages, results_per_page)
            try:
                pages = paginator.page(page)
            except PageNotAnInteger:
                pages = paginator.page(1)
            except EmptyPage:
                pages = paginator.page(paginator.num_pages)

            variables = {'pages': pages, 'author': author,
                         'page_count': page_count}
        except Exception as error:
            self.__log.error(
                f'Error in the method method page_category_wise in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'pages': '', 'author': author,
                         'page_count': page_count}
        return HttpResponse(template.render(variables, request))


    def page_tag_wise(self, request, slug):
        try:
            pages = MasterDA().get_all_pages(tags__contains=str(slug), status=1, active=1)
            tag = slug
            MasterData().create_popular_tags(tag)
            page_count = pages.count()
            template = get_template('pages/page_tags_wise.html')
            page = request.GET.get('page')
            results_per_page = 10
            paginator = Paginator(pages, results_per_page)
            try:
                pages = paginator.page(page)
            except PageNotAnInteger:
                pages = paginator.page(1)
            except EmptyPage:
                pages = paginator.page(paginator.num_pages)

            variables = {'pages': pages, 'page_count': page_count, 'tag': tag}
        except Exception as error:
            self.__log.error(
                f'Error in the method method page_tag_wise in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'pages': '', 'page_count': page_count, 'tag': tag}
        return HttpResponse(template.render(variables, request))


    def search_results(self, request):
        try:
            if request.method == 'POST':
                search = request.session['search_term'] = request.POST.get(
                    'search_term')
            search = request.session['search_term']
            pages = MasterDA().get_searh_pages(str(search))
            page_count = pages.count()
            page = request.GET.get('page')
            results_per_page = 10
            paginator = Paginator(pages, results_per_page)
            try:
                pages = paginator.page(page)
            except PageNotAnInteger:
                pages = paginator.page(1)
            except EmptyPage:
                pages = paginator.page(paginator.num_pages)
            template = get_template('pages/search_results.html')
            variables = {'pages': pages,
                         'page_count': page_count, 'search': search}
        except Exception as error:
            self.__log.error(
                f'Error in the method method search_results in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'pages': '',
                         'page_count': page_count, 'search': search}
        return HttpResponse(template.render(variables, request))


    def knowledge_base(self, request):
        try:
            categories = MasterDA().get_all_categories()
            categories = [{'id': cate.id, 'category': cate.category,
                        'pages': [{'id': page.id,'cat_id':page.category_id, 'page_heading': page.page_heading,
                        'permalink': page.permalink,'created_at':page.last_updated_at}
                         for page in cate.wikipages_set.filter(active=1,status=1).order_by('-last_updated_at')]}
                         for cate in categories]
            #to divide the categories into to sections
            category_length = []
            for cnt in  categories:
                if len(cnt['pages']) > 0:
                    for x in cnt['pages']:
                        category_length.append(x['cat_id'])
            cate_div = int(len(set(category_length))/2)
            #--end--#
            # print(cate_div)
            variables = {'categories': categories,'cate_div':cate_div}
            template = get_template('pages/knowledge_base.html')
        except Exception as error:
            self.__log.error(
                f'Error in the method method knowledge_base in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            variables = {'categories': categories,'cate_div':cate_div}
        return HttpResponse(template.render(variables, request))


    def sub_category(self, request):
        try:
            category_id = request.POST.get('category')
            sub_category = MasterDA().get_sub_categories(category_id)
            options = "<option value=''>-----</option>"
            for option in sub_category:
                options += f'<option value="{option.id}">' + \
                    option.sub_category+'</option>'
            return HttpResponse(options)
        except Exception as error:
            self.__log.error(
                f'Error in the method method sub_category in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            return HttpResponse(options)


    def like_page(self, request):
        try:
            user_id = request.user.id
            data = request.POST.get('like').split('_')
            page_id = data[0]
            liked = data[1]
            dto = SimpleNamespace()
            dto.page_id = page_id
            dto.user_id = user_id
            dto.is_liked = liked
            like = MasterData().create_liked_page(data=dto)
            if like:
                return HttpResponse(1)
            else:
                return HttpResponse(0)
        except Exception as error:
            self.__log.error(
                f'Error in the method method like_page in MasterBL., Error: {str(error)},'
                f'Error traceback: {self.__exception.exception()}'
            )
            return HttpResponse(0)


    def handler404(request, exception=None):
        template = get_template('exception_handler/404.html')
        variables = {'msg': 'page not found'}
        return HttpResponse(template.render(variables, request), status=404)


    def handler500(request, exception=None):
        template = get_template('exception_handler/500.html')
        variables = {'msg': 'internal server'}
        return HttpResponse(template.render(variables, request), status=500)


    def handler403(request, exception=None):
        template = get_template('exception_handler/403.html')
        variables = {'msg': 'access denied'}
        return HttpResponse(template.render(variables, request), status=403)
