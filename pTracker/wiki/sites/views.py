from pTracker.wiki.sites.admin_bl import AdminBl
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from pTracker.wiki.sites.auth_bl import AuthBL
from pTracker.wiki.sites.home_bl import HomeBL
from pTracker.wiki.sites.master_bl import MasterBL
from pTracker.wiki.sites.versioning_bl import Versioning_BL
from pTracker.wiki.sites.wiki_decorators import admin_only, is_confidential
# Create your views here.


def home(request):
    return HomeBL().home(request)


def login(request):
    return AuthBL().login(request)

def token_challenge(request):
    return AuthBL().token_challenge(request)


def logout(request):
    auth.logout(request)
    return redirect('home')


@login_required(login_url='login')
def add_page(request):
    return MasterBL().add_page(request)


@login_required(login_url='login')
def edit_page(request, slug):
    return MasterBL().edit_page(request, slug)


@login_required(login_url='login')
def manage_attachments(request,slug):
    return MasterBL().manage_attachments(request,slug)


@login_required(login_url='login')
def remove_attachments(request,slug,page_id):
    return MasterBL().remove_attachments(request,slug,page_id)


def sub_category(request):
    return MasterBL().sub_category(request)


def articles(request):
    return MasterBL().articles(request)

@is_confidential
def article(request, slug, permalink):
    return MasterBL().article(request, slug, permalink)

@is_confidential
def make_article_as_pdf(request,slug,permalink):
    return MasterBL().make_article_as_pdf(request,slug)


def page_category_wise(request, slug):
    return MasterBL().page_category_wise(request, slug)


def page_author_wise(request, slug):
    return MasterBL().page_author_wise(request, slug)


def page_tag_wise(request, slug):
    return MasterBL().page_tag_wise(request, slug)


def search_results(request):
    return MasterBL().search_results(request)


def knowledge_base(request):
    return MasterBL().knowledge_base(request)


def like_page(request):
    return MasterBL().like_page(request)

@is_confidential
def page_history(request,slug,permalink = None):
    return Versioning_BL().page_history(request, slug)


def compare_page_history(request):
    return Versioning_BL().compare_page_history(request)

@is_confidential
def view_page_source_history(request, type, slug):
    return Versioning_BL().view_page_source_history(request, type, slug)


@login_required(login_url='login')
def my_articles(request):
    return MasterBL().my_articles(request)


@login_required(login_url='login')
def my_articles_datatable(request):
    return MasterBL().my_articles_datatable(request)

# admin functions starts here
@login_required(login_url='login')
@admin_only
def admin_all_page_list(request):
    return AdminBl().admin_all_page_list(request)


@login_required(login_url='login')
@admin_only
def admin_page_list(request):
    return AdminBl().admin_page_list(request)


@login_required(login_url='login')
@admin_only
def admin_remove_page(request,slug):
    return AdminBl().admin_remove_page(request,slug)


@login_required(login_url='login')
@admin_only
def admin_edited_page_list(request):
    return AdminBl().admin_edited_page_list(request)


@login_required(login_url='login')
@admin_only
def admin_remove_edited_page(request,slug):
    return AdminBl().admin_remove_edited_page(request,slug)


@login_required(login_url='login')
@admin_only
def admin_view_page(request,slug):
    return AdminBl().admin_view_page(request,slug)


@login_required(login_url='login')
@admin_only
def admin_view_edited_page(request,slug):
    return AdminBl().admin_view_edited_page(request,slug)


@login_required(login_url='login')
@admin_only
def admin_compare_edited_page_with_page(request,page_id,page_id2):
    return AdminBl().admin_compare_edited_page_with_page(request,page_id,page_id2)


@login_required(login_url='login')
@admin_only
def admin_change_page_status(request,slug):
    return AdminBl().admin_change_page_status(request,slug)


@login_required(login_url='login')
@admin_only
def admin_change_edited_page_status(request,slug):
    return AdminBl().admin_change_edited_page_status(request,slug)


@login_required(login_url='login')
@admin_only
def admin_page_categories_list(request):
    return AdminBl().admin_page_categories_list(request)


@login_required(login_url='login')
@admin_only
def admin_page_categories_list_datatable(request):
    return AdminBl().admin_page_categories_list_datatable(request)


@login_required(login_url='login')
@admin_only
def admin_add_page_categories(request):
    return AdminBl().admin_add_page_categories(request)


@login_required(login_url='login')
@admin_only
def admin_edit_page_categories(request,slug):
    return AdminBl().admin_edit_page_categories(request,slug)


@login_required(login_url='login')
@admin_only
def admin_remove_page_categories(request,slug):
    return AdminBl().admin_remove_page_categories(request,slug)


@login_required(login_url='login')
@admin_only
def admin_remove_page_sub_category(request,slug):
    return AdminBl().admin_remove_page_sub_category(request,slug)


@login_required(login_url='login')
@admin_only
def admin_check_category_is_existed(request):
    return AdminBl().admin_check_category_is_existed(request)


@login_required(login_url='login')
@admin_only
def admin_check_subcategory_is_existed(request):
    return AdminBl().admin_check_subcategory_is_existed(request)


@login_required(login_url='login')
@admin_only
def admin_view_statistics(request):
    return AdminBl().admin_view_statistics(request)


@login_required(login_url='login')
@admin_only
def make_statistics_as_pdf(request):
    return AdminBl().make_statistics_as_pdf(request)


@login_required(login_url='login')
@admin_only
def make_user_wise_report(request):
    return AdminBl().make_user_wise_report(request)


def handler404(request, exception = None):
    return MasterBL().handler404(request)


def handler500(request, exception = None):
    return MasterBL().handler500(request)


def handler403(request, exception = None):
    return MasterBL().handler403(request)


