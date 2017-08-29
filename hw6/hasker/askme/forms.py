# coding=utf8
from django import forms


class QuestionForm(forms.Form):
    title = forms.CharField(max_length=200)
    text = forms.CharField(widget=forms.Textarea)
    tags = forms.CharField(required=False)

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '')
        if len(tags.split(',')) > 3:
            raise forms.ValidationError('Количество тегов должно быть не более трех')
        return tags


class UserProfileForm(forms.Form):
    username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    # todo аватарку


class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password = forms.CharField(max_length=30, widget=forms.PasswordInput)
