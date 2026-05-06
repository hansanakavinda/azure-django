# documents/admin.py

from django.contrib import admin
from .models import PDFDocument


@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):

    list_display = [
        'original_filename',
        'user',
        'file_size_kb',
        'uploaded_at',
        'is_active'
    ]
    
    list_select_related = ['user']
    list_filter = ['is_active', 'uploaded_at', 'user']
    search_fields = ['original_filename', 'user__username']
    readonly_fields = ['blob_name', 'azure_url', 'uploaded_at', 'updated_at']

    def file_size_kb(self, obj):
        return f"{obj.file_size_kb} KB"
    file_size_kb.short_description = 'Size'