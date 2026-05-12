"""
URL configuration for pdf_storage project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# pdf_storage/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings

API_V1 = 'api/v1/'

urlpatterns = [
    path(f'{API_V1}auth/', include('authentication.urls')),
    path(f'{API_V1}pdfs/', include('documents.urls')),
    path(f'{API_V1}search/', include('search.urls')),
]

if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
    
    urlpatterns += [
        path("admin/",              admin.site.urls),
        path(f"{API_V1}/schema/",   SpectacularAPIView.as_view(),                      name="schema"),
        path(f"{API_V1}/docs/",     SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]
