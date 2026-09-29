from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from chat.models import UserProfile


class SignupForm(UserCreationForm):
    display_name = forms.CharField(max_length=120, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "display_name")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("display_name", "system_prompt")
        widgets = {"system_prompt": forms.Textarea(attrs={"rows": 7})}
