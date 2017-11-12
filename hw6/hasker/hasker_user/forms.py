from django import forms


USERNAME_MAX_LEN = 30
EMAIL_MAX_LEN = 50
PASSWORD_MAX_LEN = 30


class SignUpForm(forms.Form):
    username = forms.CharField(max_length=USERNAME_MAX_LEN)
    email = forms.EmailField(max_length=EMAIL_MAX_LEN)
    password = forms.CharField(max_length=PASSWORD_MAX_LEN,
                               widget=forms.PasswordInput)
    password_confirm = forms.CharField(max_length=PASSWORD_MAX_LEN,
                                       widget=forms.PasswordInput)
    photo = forms.ImageField(required=False)

    def clean(self):
        """Password and password confirm fields must match"""
        cleaned_data = super(SignUpForm, self).clean()

        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords don't match")
        return cleaned_data


class LoginForm(forms.Form):
    username = forms.CharField(max_length=USERNAME_MAX_LEN)
    password = forms.CharField(max_length=PASSWORD_MAX_LEN,
                               widget=forms.PasswordInput)


class UserSettingsForm(forms.Form):
    username = forms.CharField(max_length=USERNAME_MAX_LEN)
    email = forms.EmailField(max_length=EMAIL_MAX_LEN)
    photo = forms.ImageField(required=False)
