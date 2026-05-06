# documents/views.py

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

# filtering and searching
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .filters import PDFDocumentFilter

from .models import PDFDocument
from .serializers import (
    PDFUploadSerializer,
    PDFDocumentSerializer,
    PDFDocumentUpdateSerializer,
    DownloadURLSerializer,
)
from .services.azure_service import azure_service

from .permissions import IsDocumentOwner


class PDFDocumentViewSet(mixins.ListModelMixin,          # GET /api/pdfs/
    mixins.RetrieveModelMixin,      # GET /api/pdfs/{id}/
    mixins.DestroyModelMixin,       # DELETE /api/pdfs/{id}/
    mixins.UpdateModelMixin,        # PATCH /api/pdfs/{id}/
    viewsets.GenericViewSet         # base class
    ):
    permission_classes = [IsAuthenticated]
    #                         ↑
    #              Every endpoint here requires login

    filterset_class = PDFDocumentFilter

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['original_filename', 'description']
    ordering_fields = ['uploaded_at', 'file_size', 'original_filename']
    ordering = ['-uploaded_at']

    def get_serializer_class(self):
        if self.action == 'upload':
            return PDFUploadSerializer
        if self.action in ['update', 'partial_update']:
            return PDFDocumentUpdateSerializer
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

    def destroy(self, request, pk=None):
        """
        DELETE /api/pdfs/{id}/

        Soft delete — marks as inactive in DB.
        Also removes from Azure.
        """
        document = self.get_object()

        # Delete from Azure first
        azure_service.delete_file(document.blob_name)

        # Soft delete in database
        document.is_active = False
        document.save()

        return Response(
            {'message': 'Document deleted successfully'},
            status=status.HTTP_200_OK
        )

    def update(self, request, pk=None, **kwargs):
        """PATCH /api/pdfs/{id}/ — update description only."""
        document = self.get_object()
        serializer = PDFDocumentUpdateSerializer(
            document,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(PDFDocumentSerializer(document).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Add these to the bottom of documents/views.py

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')

    if not username or not password:
        return Response(
            {'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already taken'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
    )
    token = Token.objects.create(user=user)

    return Response({
        'token': token.key,
        'user_id': user.id,
        'username': user.username,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    token, created = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user_id': user.id})


@api_view(['POST'])
def logout_view(request):
    request.user.auth_token.delete()
    return Response({'message': 'Logged out successfully'})