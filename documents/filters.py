# documents/filters.py

import django_filters
from .models import PDFDocument


class PDFDocumentFilter(django_filters.FilterSet):

    # Search filename (case insensitive)
    filename = django_filters.CharFilter(
        field_name='original_filename',
        lookup_expr='icontains',
        label='Filename contains'
    )

    # Date range filters
    date_from = django_filters.DateFilter(
        field_name='uploaded_at',
        lookup_expr='gte',
        label='Uploaded after'
    )
    date_to = django_filters.DateFilter(
        field_name='uploaded_at',
        lookup_expr='lte',
        label='Uploaded before'
    )

    # File size range (in bytes)
    size_min = django_filters.NumberFilter(
        field_name='file_size',
        lookup_expr='gte',
        label='Minimum size (bytes)'
    )
    size_max = django_filters.NumberFilter(
        field_name='file_size',
        lookup_expr='lte',
        label='Maximum size (bytes)'
    )

    class Meta:
        model = PDFDocument
        fields = ['filename', 'date_from', 'date_to', 'size_min', 'size_max']