from django.urls import path, include
from pTracker.wiki.sites import views
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.views import PasswordResetDoneView
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.views import PasswordResetCompleteView


urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/login/', views.login, name='login'),
    path('accounts/logout/', views.logout, name='logout'),
    path('accounts/token-challenge/', views.token_challenge, name='token_challenge'),
    path('accounts/password-reset/',PasswordResetView.as_view(template_name='auth/password_reset_form.html'),name='password_reset'),
    path('accounts/password-reset-done/',PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'),name='password_reset_done'),
    path('accounts/password-reset-confirm/<uidb64>/<token>',PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'),name='password_reset_confirm'),
    path('accounts/password-reset-complete/',PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'),name='password_reset_complete'),
    path('pages/add-page/', views.add_page, name='add_page'),
    path('pages/<slug>/edit-page/', views.edit_page, name='edit_page'),
    path('pages/<slug>/manage-attachments/', views.manage_attachments, name='manage_attachments'),
    path('pages/<slug>/<page_id>/remove-attachments/', views.remove_attachments, name='remove_attachments'),
    path('pages/articles/', views.articles, name='articles'),
    path('pages/article/<slug>/<permalink>', views.article, name='article'),
    path('pages/knowledge-base/', views.knowledge_base, name='knowledge_base'),
    path('pages/<slug>/category/', views.page_category_wise, name='page_category_wise'),
    path('pages/tags/<slug>', views.page_tag_wise, name='page_tag_wise'),
    path('pages/<slug>/author/', views.page_author_wise, name='page_author_wise'),
    path('pages/search-results', views.search_results, name='search_results'),
    path('sub-category', views.sub_category, name='sub_category'),
    path('like-page', views.like_page, name='like_page'),
    path('page-history/<slug>/<permalink>', views.page_history, name='page_history'),
    path('diffrence-between-revisions', views.compare_page_history, name='compare_page_history'),
    path('view-page-source-history/<slug>/<type>/', views.view_page_source_history, name='view_page_source_history'),
    path('my-articles', views.my_articles, name='my_articles'),
    path('my-articles-datatable', views.my_articles_datatable, name='my_articles_datatable'),
    path('pdf/<slug>/<permalink>', views.make_article_as_pdf, name='make_article_as_pdf'),
    #admin
    path('admin/all-articles/', views.admin_all_page_list, name='all_page_list'),
    path('admin/page-list/', views.admin_page_list, name='page_list'),
    path('admin/remove-page/<slug>', views.admin_remove_page, name='admin_remove_page'),
    path('admin/edited-page-list/', views.admin_edited_page_list, name='edited_page_list'),
    path('admin/remove-edited-page/<slug>', views.admin_remove_edited_page, name='admin_remove_edited_page'),
    path('admin/<slug>/view-page/', views.admin_view_page, name='admin_view_page'),
    path('admin/<slug>/view-edited-page/', views.admin_view_edited_page, name='admin_view_edited_page'),
    path('admin/<page_id>/<page_id2>/compare-pages/', views.admin_compare_edited_page_with_page, name='admin_compare_pages'),
    path('admin/<slug>/approve/', views.admin_change_page_status, name='admin_change_page_status'),
    path('admin/<slug>/approve-edited/', views.admin_change_edited_page_status, name='admin_change_edited_page_status'),
    path('admin/page/categories', views.admin_page_categories_list, name='page_categories_list'),
    path('admin/page/categories-datatable', views.admin_page_categories_list_datatable, name='page_categories_list_datatable'),
    path('admin/page/categories/add/', views.admin_add_page_categories, name='admin_add_page_categories'),
    path('admin/page/categories/<slug>/edit/', views.admin_edit_page_categories, name='admin_edit_page_categories'),
    path('admin/page/categories/<slug>/remove/', views.admin_remove_page_categories, name='admin_remove_page_categories'),
    path('admin/page/subcategories/<slug>/remove/', views.admin_remove_page_sub_category, name='admin_remove_page_sub_category'),
    path('admin/page/categories/existed/', views.admin_check_category_is_existed, name='admin_check_category_is_existed'),
    path('admin/page/subcategories/existed/', views.admin_check_subcategory_is_existed, name='admin_check_subcategory_is_existed'),
    path('admin/statistics/', views.admin_view_statistics, name='admin_view_statistics'),
    path('admin/statistics/pdf', views.make_statistics_as_pdf, name='make_statistics_as_pdf'),
    path('admin/user-wise-report/excel', views.make_user_wise_report, name='make_user_wise_report'),
]

# handler500 = views.handler500
# handler404 = views.handler404
# handler403 = views.handler403