# documents/serializers.py

from rest_framework import serializers
from django.conf import settings
from .models import PDFDocument, UploadBatch
import magic        # pip install python-magic (detects real file type)


class PDFUploadSerializer(serializers.Serializer):
    """
    Used ONLY for validating the incoming upload request.
    Not tied to the model directly because we handle
    saving manually in the view.
    """

    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        max_length=20,          # max 20 files at once
        error_messages={
            'max_length': 'You can upload a maximum of 20 files at once.',
            'allow_empty': 'Please provide at least one file.',
        }
    )

    job_description  = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=5000,
    )

    search_all = serializers.BooleanField(required=False, default=True)


    def validate_files(self, files):
        """
        Validate every file in the list.
        Collect ALL errors before returning
        so the user knows everything that is wrong at once.
        """
        errors = []

        for index, file in enumerate(files):
            file_errors = []

            # Check file size
            if file.size > settings.MAX_UPLOAD_SIZE:
                max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
                file_errors.append(
                    f"File too large. Maximum size is {max_mb}MB. "
                    f"Your file is {file.size / (1024*1024):.2f}MB"
                )

            # Check it is actually a PDF by reading the file header
            # This is more reliable than checking the extension
            file.seek(0)                        # go to start of file
            header = file.read(8)               # read first 8 bytes
            mime_type = magic.from_buffer(file.read(2048), mime=True)
            file.seek(0)                        # reset back to start

            if mime_type not in settings.ALLOWED_FILE_TYPES:
                file_errors.append(
                    f"Invalid file type: {mime_type}. "
                    "Please upload PDF files only."
                )

            # PDF files always start with %PDF
            if not header.startswith(b'%PDF'):
                file_errors.append(
                    "File is not a valid PDF. "
                    "Please upload PDF files only."
                )

            # Check filename length
            if len(file.name) > 255:
                file_errors.append("Filename is too long.")

            if file_errors:
                errors.append({
                    'file_index': index,
                    'filename': file.name,
                    'errors': file_errors,
                })

        if errors:
            raise serializers.ValidationError(errors)

        return files

class UploadBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadBatch
        fields = ['id', 'job_description', 'search_all']

class PDFDocumentSerializer(serializers.ModelSerializer):
    """
    Used for returning PDF document data in responses.
    """

    # Extra computed fields
    file_size_kb = serializers.ReadOnlyField()
    file_size_mb = serializers.ReadOnlyField()
    owner = serializers.CharField(
        source='user.username',
        read_only=True
    )

    class Meta:
        model = PDFDocument
        fields = [
            'id',
            'original_filename',
            'file_size',
            'file_size_kb',
            'file_size_mb',
            'uploaded_at',
            'updated_at',
            'owner',
            # Note: we do NOT return blob_name or azure_url directly
            # Users get a temporary download URL through a separate endpoint
        ]
        read_only_fields = [
            'id', 'original_filename', 'file_size',
            'uploaded_at', 'updated_at', 'owner',
        ]


class DownloadURLSerializer(serializers.Serializer):
    """
    Used for returning a temporary download URL.
    """
    download_url = serializers.URLField()
    expires_at = serializers.DateTimeField()
    expires_in_hours = serializers.IntegerField()
    filename = serializers.CharField()