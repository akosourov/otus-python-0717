from django import forms


class UserProfileForm(forms.Form):
    username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    photo = forms.ImageField()
