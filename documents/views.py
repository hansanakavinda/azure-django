# documents/views.py

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# filtering and searching
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .filters import PDFDocumentFilter

from .models import PDFDocument
from .serializers import (
    PDFUploadSerializer,
    PDFDocumentSerializer,
    DownloadURLSerializer,
)
from .services.azure_service import azure_service

from .permissions import IsDocumentOwner


class PDFDocumentViewSet(
    mixins.ListModelMixin,          # GET /api/pdfs/
    mixins.RetrieveModelMixin,      # GET /api/pdfs/{id}/
    viewsets.GenericViewSet         # base class
    ):

    permission_classes = [IsAuthenticated] # check if user is authenticated

    filterset_class = PDFDocumentFilter

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['original_filename', 'description']
    ordering_fields = ['uploaded_at', 'file_size', 'original_filename']
    ordering = ['-uploaded_at']

    def get_serializer_class(self):
        if self.action == 'upload':
            return PDFUploadSerializer
        if self.action == 'download':
            return DownloadURLSerializer
        return PDFDocumentSerializer

    def get_queryset(self):
        """
        CRITICAL: Users can only see their own documents.
        Filter by the logged-in user always.
        """
        return PDFDocument.objects.filter(
            user=self.request.user,
            is_active=True
        )

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        POST /api/pdfs/upload/

        Accept multiple PDF files, upload to Azure,
        save metadata to database.

        Best effort — upload as many as possible,
        report failures without stopping.
        """
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        files = serializer.validated_data['files']
        description = serializer.validated_data.get('description', '')

        results = []
        success_count = 0
        fail_count = 0

        for file in files:
            try:
                # Upload to Azure
                azure_result = azure_service.upload_file(
                    file=file,
                    user_id=request.user.id,
                    original_filename=file.name,
                )

                # Save metadata to database
                document = PDFDocument.objects.create(
                    user=request.user,
                    original_filename=file.name,
                    blob_name=azure_result['blob_name'],
                    azure_url=azure_result['azure_url'],
                    file_size=file.size,
                    description=description,
                )

                results.append({
                    'filename': file.name,
                    'status': 'success',
                    'document': PDFDocumentSerializer(document).data,
                })
                success_count += 1

            except Exception as e:
                results.append({
                    'filename': file.name,
                    'status': 'failed',
                    'error': str(e),
                })
                fail_count += 1

        # Choose response status based on results
        if success_count == 0:
            response_status = status.HTTP_400_BAD_REQUEST
        elif fail_count > 0:
            response_status = status.HTTP_207_MULTI_STATUS
            #                        ↑
            #              207 = Multi-Status
            #              Means "some worked, some did not"
        else:
            response_status = status.HTTP_201_CREATED

        return Response({
            'uploaded': success_count,
            'failed': fail_count,
            'total': len(files),
            'results': results,
        }, status=response_status)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        GET /api/pdfs/{id}/download/

        Returns a temporary signed URL for downloading the file.
        URL expires after 1 hour.
        """
        document = self.get_object()
        #               ↑
        #   get_object() checks that document belongs
        #   to request.user automatically because of get_queryset()
        #   If not found → 404 automatically

        url_data = azure_service.generate_download_url(
            blob_name=document.blob_name,
            expiry_hours=1,
        )

        return Response({
            **url_data,
            'filename': document.original_filename,
        })

    
