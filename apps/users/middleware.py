from django.shortcuts import redirect


class RoleRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            if not request.user.role:
                allowed_paths = [
                    'select-role',
                    'logout',
                    '/accounts/',
                    '/admin/',
                    '/static/',
                    '/media/',
                ]
                if not any(p in request.path for p in allowed_paths):
                    return redirect('/users/select-role/')
        return self.get_response(request)