# documents/models.py

from django.db import models
from django.contrib.auth.models import User
import uuid

class UploadBatch(models.Model):
    """
    Represents one bulk upload request.
    A batch has:
    - one batch_id
    - one job description
    - one search mode (all PDFs or only this batch)
    - many PDF documents
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='upload_batches'
    )

    job_description = models.TextField()

    search_all = models.BooleanField(
        default=True,
        help_text='If true, search against all PDFs. If false, search only this batch.'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Batch {self.id} - {self.user.username}"

class PDFDocument(models.Model):
    """
    Stores metadata about uploaded PDFs.
    The actual file lives in Azure Blob Storage.
    We only store information ABOUT the file here.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    batch = models.ForeignKey(
        UploadBatch,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )

    # Original filename the user uploaded
    original_filename = models.CharField(max_length=500)

    # The path/name inside Azure container
    # Example: user_1/2024-01-15/abc123_resume.pdf
    blob_name = models.CharField(max_length=1000, unique=True)

    # Full URL to access the file in Azure
    azure_url = models.URLField(max_length=2000)

    # File info
    file_size = models.PositiveBigIntegerField(help_text='File size in bytes')

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft delete — do not actually remove from DB
    # just mark as inactive
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']         # newest first by default
        indexes = [
            models.Index(fields=['user', 'uploaded_at']),
            models.Index(fields=['user', 'is_active']),
            #               ↑
            #   Indexes make filtering faster
            #   These are the fields we will filter on most
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.user.username})"

    @property
    def file_size_kb(self):
        """Return file size in KB for display."""
        return round(self.file_size / 1024, 2)

    @property
    def file_size_mb(self):
        """Return file size in MB for display."""
        return round(self.file_size / (1024 * 1024), 2)