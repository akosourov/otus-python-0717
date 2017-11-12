# coding=utf8
from django import forms


class MultiTagField(forms.Field):
    def to_python(self, value):
        if not value:
            return []
        value = value.strip()
        if ',' in value:
            sep = ','
        else:
            sep = ' '
        return [s.strip() for s in value.split(sep)]


class QuestionForm(forms.Form):
    title = forms.CharField(max_length=200)
    text = forms.CharField(widget=forms.Textarea)
    tags = MultiTagField(required=False)

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', [])
        if len(tags) > 3:
            raise forms.ValidationError('Количество тегов должно быть не более трех')
        return tags
