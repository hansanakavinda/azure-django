# search/models.py

from django.db import models
from django.contrib.auth.models import User
from documents.models import UploadBatch
import uuid


class SearchResult(models.Model):
    """
    Stores individual candidate ranking results.
    Populated ONLY through the webhook.
    Users can only read — no create, update, delete.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    batch = models.ForeignKey(
        UploadBatch,
        on_delete=models.CASCADE,
        related_name='search_results'
    )

    # Which user this result belongs to
    # Denormalized from batch for faster queries
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='search_results'
    )

    candidate_id = models.CharField(max_length=500)
    score = models.FloatField()
    rank = models.PositiveIntegerField()

    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['batch', 'rank']
        indexes = [
            models.Index(fields=['batch', 'rank']),
            models.Index(fields=['user', 'batch']),
            models.Index(fields=['candidate_id']),
        ]
        # One candidate can only appear once per batch
        constraints = [
            models.UniqueConstraint(
                fields=['batch', 'candidate_id'],
                name='unique_candidate_per_batch'
            )
        ]

    def __str__(self):
        return f"Rank {self.rank}: {self.candidate_id} ({self.score})"