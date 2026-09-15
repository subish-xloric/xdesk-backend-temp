from django import template
from django.db.models import Count
from django.utils.safestring import mark_safe
import re
from pTracker.wiki.data_access.replica.master_da import MasterDA
register = template.Library()


@register.filter
def highlight_search(text, search):
    # highlighted = text.replace(search, f'<span class="highlight">{search}</span>')
    highlighted = re.compile(re.escape(str(search)), re.IGNORECASE)
    highlighted = highlighted.sub(
        f'<span class="highlight">{search}</span>', text)
    return mark_safe(highlighted)

@register.simple_tag
def get_author(user_id):
    user = MasterDA().get_author(user_id)
    return user.first_name

@register.simple_tag
def popular_articles():
    popular_articles = MasterDA().get_popular_articles()
    return popular_articles

@register.simple_tag
def latest_articles():
    latest_articles = MasterDA().get_latest_articles()
    return latest_articles

@register.simple_tag
def popular_tags():
    popular_tags = MasterDA().get_popular_tags()
    return popular_tags

def master_menu_access(user):
    print(user)

