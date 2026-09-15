from django import forms

class ApproveForm(forms.Form):
    CHOICES = [('','-----'),('1','Approved'),('2','Rejected')]
    status = forms.ChoiceField(choices=CHOICES)
    remarks = forms.CharField(required=False,widget=forms.Textarea(attrs={'rows':4}))

    def clean(self):
        cleaned_data = super(ApproveForm, self).clean()
        status = cleaned_data.get('status')
        remarks = cleaned_data.get('remarks')
        if status in ('', 'None', None):
            self._errors["status"] = self.error_class(
                ['Please select a status'])
            if status in cleaned_data:
                del cleaned_data["status"]
        if status == 2:
            if remarks in ('', 'None', None):
                self._errors["remarks"] = self.error_class(
                    ['Please provide a reason for rejection'])
                if remarks in cleaned_data:
                    del cleaned_data["remarks"]

        return cleaned_data

