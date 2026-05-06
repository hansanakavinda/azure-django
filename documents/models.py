# documents/models.py

from django.db import models
from django.contrib.auth.models import User


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

    # Original filename the user uploaded
    original_filename = models.CharField(max_length=500)

    # The path/name inside Azure container
    # Example: user_1/2024-01-15/abc123_resume.pdf
    blob_name = models.CharField(max_length=1000, unique=True)

    # Full URL to access the file in Azure
    azure_url = models.URLField(max_length=2000)

    # File info
    file_size = models.PositiveBigIntegerField(help_text='File size in bytes')
    description = models.TextField(blank=True, default='')

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