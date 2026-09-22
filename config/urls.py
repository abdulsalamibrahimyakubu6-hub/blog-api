"""URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root_view(request):
    return JsonResponse({
        "message": "Welcome to the Blog & MicroPost REST API",
        "endpoints": {
            "register": "/api/auth/register/",
            "token": "/api/auth/token/",
            "token_refresh": "/api/auth/token/refresh/",
            "me": "/api/auth/me/",
            "posts": "/api/posts/",
            "comments": "/api/comments/",
            "microposts": "/api/microposts/",
            "admin": "/admin/"
        }
    })


from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", api_root_view, name="home"),
    path("admin/", admin.site.urls),
    path("api/", include("blog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    from django.views.static import serve
    from django.urls import re_path
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

