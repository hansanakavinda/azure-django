# search/admin.py

from django.contrib import admin
from .models import SearchResult


@admin.register(SearchResult)
class SearchResultAdmin(admin.ModelAdmin):
    list_display = [
        'rank', 'candidate_id', 'score',
        'batch', 'user', 'received_at'
    ]
    list_filter = ['user', 'received_at']
    search_fields = ['candidate_id']
    readonly_fields = [
        'id', 'batch', 'user', 'candidate_id',
        'score', 'rank', 'received_at'
    ]

    # Disable all modifications in admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False