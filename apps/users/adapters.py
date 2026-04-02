from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        return '/users/select-role/'

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.role = ''
        user.save(update_fields=['role'])
        return user

    def get_login_redirect_url(self, request):
        user = request.user
        if not user.role:
            return '/users/select-role/'
        return '/dashboard/'