# search/services.py

from azure.cosmos import CosmosClient, exceptions
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CosmosCandidateService:
    """
    Handles read operations from Azure Cosmos DB (NoSQL Core API)
    for Candidate profile documents.
    """

    def __init__(self):
        try:
            self.client = CosmosClient(
                url=settings.COSMOS_URI,
                credential=settings.COSMOS_KEY
            )
            self.database = self.client.get_database_client(settings.COSMOS_DATABASE)
            self.container = self.database.get_container_client(settings.COSMOS_CONTAINER)
        except Exception as e:
            logger.warning(f"CosmosDB Client initialization failed (Using dummy settings?): {e}")
            self.container = None

    def get_candidate_by_id(self, candidate_id):
        """
        Fetches a single candidate document using a highly optimized Point Read.
        In Cosmos DB, Point Read is the fastest and cheapest read operation (1 RU).
        """
        if not self.container:
            return {"success": False, "error": "Cosmos DB not initialized."}

        try:
            # Point Read: requires both item ID and partition_key
            # candidate_id acts as both in our schema design
            candidate_doc = self.container.read_item(
                item=str(candidate_id),
                partition_key=str(candidate_id)
            )
            return {
                "success": True,
                "data": candidate_doc
            }
        except exceptions.CosmosResourceNotFoundError:
            return {
                "success": False,
                "error": f"Candidate with ID {candidate_id} not found."
            }
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Cosmos DB Error during point read: {e}")
            return {
                "success": False,
                "error": "Error reading candidate profile from external database."
            }

    def get_all_candidates_paginated(self, max_items=10, continuation_token=None):
        """
        Queries all candidate profiles using Cosmos DB continuation token pagination.
        """
        if not self.container:
            return {"success": False, "error": "Cosmos DB not initialized."}

        try:
            query = "SELECT * FROM c"
            
            # Use by_page iterator to handle server-side pagination with continuation tokens
            query_iterable = self.container.query_items(
                query=query,
                enable_cross_partition_query=True,
                max_item_count=max_items
            )
            
            pager = query_iterable.by_page(continuation_token)
            current_page = list(next(pager))
            next_token = pager.continuation_token

            return {
                "success": True,
                "data": current_page,
                "next_page_token": next_token
            }
        except StopIteration:
            # No more records left
            return {
                "success": True,
                "data": [],
                "next_page_token": None
            }
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Cosmos DB Error during query: {e}")
            return {
                "success": False,
                "error": "Failed to fetch candidates page."
            }

# Instantiate singleton service instance
cosmos_candidate_service = CosmosCandidateService()