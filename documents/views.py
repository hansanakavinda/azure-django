# documents/views.py
from pdf_storage import settings

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# filtering and searching
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .filters import PDFDocumentFilter

from .models import PDFDocument, UploadBatch
from .serializers import (
    PDFUploadSerializer,
    PDFDocumentSerializer,
    DownloadURLSerializer,
    UploadBatchSerializer,
)
from .services.azure_service import azure_service
from .permissions import IsDocumentOwner
from pdf_storage.responses import success_response, error_response
from pdf_storage.throttles import PdfThrottle, UploadThrottle

# local testing
import os
from django.conf import settings



class PDFDocumentViewSet(
    mixins.ListModelMixin,          # GET /api/pdfs/
    mixins.RetrieveModelMixin,      # GET /api/pdfs/{id}/
    viewsets.GenericViewSet         # base class
    ):

    permission_classes = [IsAuthenticated] # check if user is authenticated
    throttle_scope = 'pdfs' # apply rate limiting
    filterset_class = PDFDocumentFilter

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['original_filename', 'description']
    ordering_fields = ['uploaded_at', 'file_size', 'original_filename']
    ordering = ['-uploaded_at']

    def get_serializer_class(self):
        if self.action in ['upload', 'test_upload']:
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

    def list(self, request, *args, **kwargs):
        """
        GET /api/pdfs/
        """

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        # If pagination is enabled
        if page is not None:

            serializer = self.get_serializer(page, many=True)

            paginated_response = self.get_paginated_response(
                serializer.data
            )

            return success_response(
                data={
                    'count': paginated_response.data['count'],
                    'next': paginated_response.data['next'],
                    'previous': paginated_response.data['previous'],
                    'documents': paginated_response.data['results'],
                },
                message='Documents retrieved successfully.',
            )

        # If pagination is NOT enabled
        serializer = self.get_serializer(queryset, many=True)

        return success_response(
            data={
                'documents': serializer.data,
            },
            message='Documents retrieved successfully.',
        )

    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/pdfs/{id}/
        """

        instance = self.get_object()

        serializer = self.get_serializer(instance)

        return success_response(
            data=serializer.data,
            message='Document retrieved successfully.',
        )


    @action(detail=False, methods=['post'], url_path='test-upload')
    def test_upload(self, request):
        """
        POST /api/pdfs/test-upload/

        Same validation as the real upload endpoint.
        Saves files locally instead of Azure.
        No database records created.
        For testing purposes only.
        """
        serializer = PDFUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        files = serializer.validated_data['files']
        results = []
        success_count = 0
        fail_count = 0

        # Create uploads directory if it does not exist
        upload_dir = settings.MEDIA_ROOT
        os.makedirs(upload_dir, exist_ok=True)

        for file in files:
            try:
                # Build a safe unique filename
                # Same logic as azure service but saves locally
                from datetime import datetime
                import uuid

                date_str = datetime.now().strftime('%Y-%m-%d')
                unique_id = str(uuid.uuid4())[:8]
                safe_filename = "".join(
                    c for c in file.name
                    if c.isalnum() or c in '._-'
                ).strip()

                final_filename = f"{date_str}_{unique_id}_{safe_filename}"
                file_path = os.path.join(upload_dir, final_filename)

                # Write the file to disk
                with open(file_path, 'wb') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                        #                  ↑
                        #   chunks() reads the file in pieces
                        #   important for large files
                        #   avoids loading entire file into memory

                results.append({
                    'filename': file.name,
                    'status': 'success',
                    'saved_as': final_filename,
                    'local_path': file_path,
                    'accessible_at': request.build_absolute_uri(
                        f"{settings.MEDIA_URL}{final_filename}"
                    ),
                    'file_size': file.size,
                })
                success_count += 1

            except Exception as e:
                results.append({
                    'filename': file.name,
                    'status': 'failed',
                    'error': str(e),
                })
                fail_count += 1

        if success_count == 0:
            response_status = status.HTTP_400_BAD_REQUEST
        elif fail_count > 0:
            response_status = status.HTTP_207_MULTI_STATUS
        else:
            response_status = status.HTTP_201_CREATED

        return Response({
            'uploaded': success_count,
            'failed': fail_count,
            'total': len(files),
            'save_location': str(settings.MEDIA_ROOT),
            'results': results,
        }, status=response_status)

    @action(detail=False, methods=['post'], throttle_classes=[UploadThrottle])
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
            return error_response(
                errors=serializer.errors,
                message="Validation failed."
            )

        files = serializer.validated_data['files']
        job_description = serializer.validated_data.get('job_description', '')
        search_all = serializer.validated_data.get('search_all', True)

        is_search_request = bool(job_description.strip())

        batch = None
        if is_search_request:
            batch = UploadBatch.objects.create(
                user=request.user,
                job_description=job_description,
                search_all=search_all
            )

        results = []
        success_count = 0
        fail_count = 0

        for file in files:
            try:
                blob_metadata = None

                if batch:
                    blob_metadata = {
                        'batch_id': str(batch.id),
                    }

                # Upload to Azure
                azure_result = azure_service.upload_file(
                    file=file,
                    user_id=request.user.id,
                    original_filename=file.name,
                    metadata=blob_metadata
                )

                # Save metadata to database
                document = PDFDocument.objects.create(
                    user=request.user,
                    batch=batch,
                    original_filename=file.name,
                    blob_name=azure_result['blob_name'],
                    azure_url=azure_result['azure_url'],
                    file_size=file.size,
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
            return error_response(
                errors=results,
                message="All uploads failed.",
                status_code=response_status
            )

        # Build response
        response_data = {
            'uploaded': success_count,
            'failed': fail_count,
            'total': len(files),
            'results': results,
        }

        if batch and success_count > 0:
            try:
                signal_data = {
                    'batch_id': str(batch.id),
                    'job_description': job_description,
                    'search_all': search_all,
                    'callback_url': f"{settings.WEBHOOK_BASE_URL}/api/search/webhook/",
                }

                azure_service.upload_signal_file(
                    batch_id=batch.id,
                    signal_data=signal_data,
                )

            except Exception as e:
                return error_response(
                    errors={'signal': str(e)},
                    message='Files uploaded but failed to start processing.',
                    data=response_data,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return success_response(
            data=response_data,
            message="Files uploaded with some failures." if fail_count > 0 else "All files uploaded successfully.",
            status_code=status.HTTP_201_CREATED,
        )

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
        if not document:
            return error_response(
                errors='Document not found.',
                message="Document not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        url_data = azure_service.generate_download_url(
            blob_name=document.blob_name,
            expiry_hours=1,
        )

        return success_response(
            data={
                **url_data,
                'filename': document.original_filename,
            },
            message="Download URL generated successfully."
        )

    
