from django import forms
import base64
from pTracker.wiki.data_access.wiki_models.models import WikiCategories
from pTracker.wiki.data_access.wiki_models.models import WikiPages
from django.contrib.auth.models import User

class AddPageForm(forms.Form):
        def __init__(self, *arg, **kwargs):
            super(AddPageForm, self).__init__(*arg, **kwargs)
            CHOICES = [('','-----')]+[(category.id, category.category) 
                    for category in WikiCategories.objects.all().order_by('category')]
            APPROVER = [('','-----')]+[(user.id, str(user.first_name)+' '+str(user.last_name)) 
                    for user in User.objects.filter(groups__id__lt =  5)]
            self.fields['category'].choices = CHOICES
            self.fields['approver'].choices = APPROVER

        page_heading = forms.CharField(label='Heading', min_length=3, max_length=100)
        category = forms.ChoiceField()
        approver = forms.ChoiceField()
        page_content = forms.CharField(label='Content', required=True)

        def clean(self):
            cleaned_data = super(AddPageForm, self).clean()
            page_heading = cleaned_data.get('page_heading')
            if page_heading in ('', 'None', None):
                self._errors["page_heading"] = self.error_class(
                    ['Please enter a page heading'])
                if page_heading in cleaned_data:
                    del cleaned_data["page_heading"]
            elif  WikiPages.objects.filter(page_heading = page_heading).exists():
                self._errors["page_heading"] = self.error_class(
                    ['The heading is already existed in the database. Please try something diifrent'])
                if page_heading in cleaned_data:
                    del cleaned_data["page_heading"]

            category = cleaned_data.get('category')
            if category in ('', 'None', None):
                self._errors["category"] = self.error_class(
                    ['Please select a category'])
                if category in cleaned_data:
                    del cleaned_data["category"]

            approver = cleaned_data.get('approver')
            if approver in ('', 'None', None):
                self._errors["approver"] = self.error_class(
                    ['Please select an approver'])
                if approver in cleaned_data:
                    del cleaned_data["approver"]


            return cleaned_data


class EditPageForm(forms.Form):
        def __init__(self, *arg, **kwargs):
            super(EditPageForm, self).__init__(*arg, **kwargs)
            CHOICES = [('','-----')]+[(category.id, category.category)
                   for category in WikiCategories.objects.all().order_by('category')]
            APPROVER = [('','-----')]+[(user.id, str(user.first_name)+' '+str(user.last_name))
                   for user in User.objects.filter(groups__id__lt = 5)]
            self.fields['category'].choices = CHOICES
            self.fields['approver'].choices = APPROVER



        category = forms.ChoiceField()
        page_content = forms.CharField(label='Page Content', required=True)
        approver = forms.ChoiceField()

        def clean(self):
            cleaned_data = super(EditPageForm, self).clean()
            page_id = cleaned_data.get('page_id')
            page_content = cleaned_data.get('page_content')
            page = WikiPages.objects.get(id = self.data["page_id"])
            page_content1 = page.page_content.replace('&nbsp;', '').replace('<p>&nbsp;</p>','')
            page_content1 = page_content1.replace('\n', ' ').replace('\r', '').replace(' ', '')
            page_content2 = page_content.replace('&nbsp;', '').replace('<p>&nbsp;</p>','')
            page_content2 = page_content2.replace('\n', ' ').replace('\r', '').replace(' ', '')

            if page_content in ('', 'None', None):
                self._errors["page_content"] = self.error_class(
                    ['Content section cannot be blank'])
                if page_content in cleaned_data:
                    del cleaned_data["page_content"]
            # elif  page_content2 == page_content1:
            #     self._errors["page_content"] = self.error_class(
            #         ['The content is already existed in the database. Please modify the content and retry'])
            #     if page_content in cleaned_data:
            #         del cleaned_data["page_content"]
                    
            approver = cleaned_data.get('approver')
            if approver in ('', 'None', None):
                self._errors["approver"] = self.error_class(
                    ['Please select an approver'])
                if approver in cleaned_data:
                    del cleaned_data["approver"]

            return cleaned_data



