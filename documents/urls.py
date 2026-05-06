# documents/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pdfs', views.PDFDocumentViewSet, basename='pdf')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', views.register),
    path('auth/login/', views.login_view),
    path('auth/logout/', views.logout_view),
]