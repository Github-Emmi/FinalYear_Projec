from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import RememberToken

class RememberMeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            token = request.COOKIES.get('remember_token')
            if token:
                try:
                    remember = RememberToken.objects.select_related('user').get(token=token)
                    login(request, remember.user)
                except RememberToken.DoesNotExist:
                    pass
        return self.get_response(request)
        
