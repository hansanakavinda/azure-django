# search/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.SearchResultViewSet, basename='search-result')

urlpatterns = [
    path('results/', include(router.urls)),
    path('webhook/', views.webhook_receive, name='search-webhook'), 
    path('candidates/<str:candidate_id>/', views.retrieve_candidate, name='candidate-detail'),
    path('test-candidates/', views.test_list_candidates, name='test-candidate-list'),
    path('test-candidates/<str:candidate_id>/', views.test_retrieve_candidate, name='test-candidate-detail'),
    
    
]