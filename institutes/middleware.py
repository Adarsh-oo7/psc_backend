from django.shortcuts import get_object_or_404
from django.http import Http404
from .models import Institute

class InstituteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.META.get('HTTP_HOST', '')
        parts = host.split('.')
        
        is_localhost = 'localhost' in host or '127.0.0.1' in host
        
        if is_localhost:
            # e.g. abc.localhost:8000 or abc.127.0.0.1.nip.io
            if len(parts) >= 2 and not parts[0].split(':')[0] in ('localhost', '127', '127.0.0.1'):
                subdomain = parts[0]
                try:
                    request.institute = Institute.objects.get(slug=subdomain)
                except (Institute.DoesNotExist, Exception):
                    request.institute = None
            else:
                request.institute = None
        else:
            # Production: e.g. abc.kpscmaster.com
            if len(parts) > 2 and parts[0] not in ('www', 'admin', 'api'):
                subdomain = parts[0]
                try:
                    request.institute = Institute.objects.get(slug=subdomain)
                except (Institute.DoesNotExist, Exception):
                    request.institute = None
            else:
                request.institute = None

        response = self.get_response(request)
        return response
