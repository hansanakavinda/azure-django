
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
import logging

from .models import SearchResult
from .serializers import (
    WebhookPayloadSerializer,
    SearchResultSerializer,
    SearchResultDetailSerializer,
)
from .services import cosmos_candidate_service
from documents.models import UploadBatch
from pdf_storage.responses import success_response, error_response

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_receive(request):
    """
    POST /api/search/webhook/

    Azure calls this when ranking is complete.
    Saves candidate results to SearchResult table.
    """
    serializer = WebhookPayloadSerializer(data=request.data)

    if not serializer.is_valid():
        return error_response(
            errors=serializer.errors,
            message='Invalid webhook payload.',
        )

    data = serializer.validated_data
    batch_id = data['batch_id']
    webhook_status = data['status']

    # Find the batch
    try:
        batch = UploadBatch.objects.get(id=batch_id)
    except UploadBatch.DoesNotExist:
        return error_response(
            message='Batch not found.',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Prevent duplicate processing
    if SearchResult.objects.filter(batch=batch).exists():
        return success_response(
            message='Results already saved for this batch.',
        )

    # Handle failure
    if webhook_status == 'failed':
        error_message = data.get('error_message', 'Processing failed.')

        logger.error(
            f"Batch {batch_id} processing failed: {error_message}"
        )

        return success_response(
            message='Failure recorded.',
            data={'error_message': error_message},
        )

    # Handle success — save results
    results = data.get('results', [])

    if not results:
        return error_response(
            message='No results in webhook payload.',
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Sort by score descending
    results.sort(key=lambda x: float(x['score']), reverse=True)

    # Save each result with rank
    created_results = []

    for rank, result in enumerate(results, 1):
        search_result = SearchResult.objects.create(
            batch=batch,
            user=batch.user,
            candidate_id=result['candidate_id'],
            score=float(result['score']),
            rank=rank,
        )
        created_results.append(search_result)

    logger.info(
        f"Batch {batch_id} completed. {len(created_results)} results saved."
    )

    return success_response(
        data={
            'batch_id': str(batch.id),
            'results_saved': len(created_results),
        },
        message='Results received and saved successfully.',
        status_code=status.HTTP_201_CREATED,
    )


class SearchResultViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    Read only viewset for search results.
    No create, update, delete.

    GET /api/search/results/                → all my results
    GET /api/search/results/{id}/           → single result detail
    GET /api/search/results/?batch_id=xxx   → results for a batch
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SearchResultDetailSerializer
        return SearchResultSerializer

    def get_queryset(self):
        """Users only see their own results."""
        queryset = SearchResult.objects.filter(user=self.request.user)

        # Filter by batch id if provided
        batch_id = self.request.query_params.get('batch_id')
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)

            return success_response(
                data={
                    'count': paginated.data['count'],
                    'next': paginated.data['next'],
                    'previous': paginated.data['previous'],
                    'results': paginated.data['results'],
                },
                message='Search results retrieved successfully.',
            )

        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data={'results': serializer.data},
            message='Search results retrieved successfully.',
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return success_response(
            data=serializer.data,
            message='Search result retrieved successfully.',
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def retrieve_candidate(request, candidate_id):
    """
    GET /api/search/candidates/{candidate_id}/

    Fetches full candidate profile from Cosmos DB.
    Only accessible if user has a search result with this candidate_id.
    """
    # Security check — user must have a result with this candidate
    has_access = SearchResult.objects.filter(
        user=request.user,
        candidate_id=candidate_id,
    ).exists()

    if not has_access:
        return error_response(
            message='Candidate not found in your search results.',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    result = cosmos_candidate_service.get_candidate_by_id(candidate_id)

    if not result['success']:
        return error_response(
            message='Failed to retrieve candidate details.',
            errors={'detail': result.get('error')},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return success_response(
        data=result['data'],
        message='Candidate details retrieved successfully.',
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_list_candidates(request):
    """
    GET /api/search/test-candidates/
    
    Returns a paginated list of all candidate profiles in Cosmos DB.
    Use query parameter 'limit' to set size, and 'page_token' to get next pages.
    """
    # Parse pagination parameters
    limit = request.query_params.get('limit', 10)
    page_token = request.query_params.get('page_token', None)

    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    result = cosmos_candidate_service.get_all_candidates_paginated(
        max_items=limit,
        continuation_token=page_token
    )

    if not result['success']:
        return error_response(
            message="Database read failed.",
            errors={"detail": result.get('error')},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return success_response(
        data={
            "candidates": result['data'],
            "next_page_token": result['next_page_token']
        },
        message="Candidates list page retrieved successfully."
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_retrieve_candidate(request, candidate_id):
    """
    GET /api/search/test-candidates/{candidate_id}/
    
    Fetches full resume analysis/details from Cosmos DB using optimized point read.
    """
    result = cosmos_candidate_service.get_candidate_by_id(candidate_id)

    if not result['success']:
        # If the candidate ID doesn't exist, return 404
        return error_response(
            message="Candidate not found.",
            errors={"detail": result.get('error')},
            status_code=status.HTTP_404_NOT_FOUND
        )

    return success_response(
        data=result['data'],
        message="Candidate details retrieved successfully."
    )