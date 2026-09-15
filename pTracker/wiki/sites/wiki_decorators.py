from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from pTracker.wiki.data_access.replica.master_da import MasterDA
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url

def admin_only(function):
    def wrap(request, *args, **kwargs):

        group = int(request.user.groups.values_list('id', flat=True).first())
        if group < 5:
             return function(request, *args, **kwargs)
        else:
             return redirect('home')

    return wrap

def is_confidential(function):
    def wrap(request, *args, **kwargs):
        article = MasterDA().get_single_page(slug=int(kwargs['slug']))
        is_confidential = article.is_confidential
        if is_confidential ==1:
             if request.user.is_authenticated:
               return function(request, *args, **kwargs)
             else:
               from django.contrib.auth.views import redirect_to_login
               path = request.get_full_path()
               resolved_login_url = resolve_url('login')
               return redirect_to_login(path, resolved_login_url, REDIRECT_FIELD_NAME)
        else:
          return function(request, *args, **kwargs)

    return wrap