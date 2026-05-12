# documents/services/azure_service.py

from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
)
from azure.core.exceptions import AzureError
from django.conf import settings
from datetime import datetime, timedelta, timezone
import uuid
import json


class AzureStorageService:
    """
    Handles all communication with Azure Blob Storage.
    Views should never import azure directly — always go through here.
    """

    def __init__(self):
        try:
            self.connection_string = settings.AZURE_CONNECTION_STRING
            self.container_name = settings.AZURE_CONTAINER_NAME
            self.client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            self.container_client = self.client.get_container_client(
                self.container_name
            )
        except Exception as e:
            # Log the error but don't crash the app on startup
            print(f"Azure Blob Storage initialization failed: {e}")
            self.client = None
            self.container_client = None

    def _generate_blob_name(self, user_id, original_filename):
        """
        Create a unique organized path for the file in Azure.

        Result: 2024-01-15/a3f9b2c1_resume.pdf
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        unique_id = str(uuid.uuid4())[:8]

        # Clean filename — remove unsafe characters
        safe_filename = "".join(
            c for c in original_filename
            if c.isalnum() or c in '._- '
        ).strip()
        safe_filename = safe_filename.replace(' ', '_')

        return f"resumes/{unique_id}_{safe_filename}"

    def upload_file(self, file, user_id, original_filename, metadata=None):
        """
        Upload a single file to Azure Blob Storage.

        Returns a dict with blob_name and azure_url on success.
        Raises an exception on failure.
        """
        blob_name = self._generate_blob_name(user_id, original_filename)

        blob_client = self.container_client.get_blob_client(blob_name)

        # Upload the file
        # overwrite=False means it will fail if blob already exists
        # since we use UUID in the name this should never happen
        blob_client.upload_blob(
            file,
            overwrite=False,
            content_settings=self._get_content_settings(),
            metadata=metadata or {}
        )

        azure_url = blob_client.url

        return {
            'blob_name': blob_name,
            'azure_url': azure_url,
        }

    def upload_signal_file(self, batch_id, signal_data):
        """
        Upload _batch_complete.json as the signal file.
        Azure Function watches for this file.
        When it appears, Azure knows all PDFs are uploaded
        and processing can begin.
        """
        blob_name = f"process_requests/batch_{batch_id}/_batch_complete.json"
        blob_client = self.container_client.get_blob_client(blob_name)

        blob_client.upload_blob(
            json.dumps(signal_data, indent=2),
            overwrite=True,
            content_settings=self._get_content_settings(
                content_type='application/json'
            ),
        )

        return blob_name
    
    def _get_content_settings(self, content_type='application/pdf'):
        """Set the content type so browsers know it is a PDF."""
        from azure.storage.blob import ContentSettings
        return ContentSettings(content_type=content_type)

    def generate_download_url(self, blob_name, expiry_hours=1):
        """
        Generate a temporary signed URL for downloading a file.

        The URL works for expiry_hours then expires automatically.
        This is the secure way to give access without making files public.
        """
        # Get the account name and key from the connection string
        account_name = self.client.account_name
        account_key = self.client.credential.account_key

        # Set expiry time
        expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

        # Generate SAS (Shared Access Signature) token
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )

        # Build the full download URL
        download_url = (
            f"https://{account_name}.blob.core.windows.net"
            f"/{self.container_name}/{blob_name}?{sas_token}"
        )

        return {
            'download_url': download_url,
            'expires_at': expiry.isoformat(),
            'expires_in_hours': expiry_hours,
        }

    def delete_file(self, blob_name):
        """
        Delete a file from Azure Blob Storage.

        Returns True on success, False if file not found.
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except AzureError:
            return False

    def file_exists(self, blob_name):
        """Check if a file exists in Azure."""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.get_blob_properties()
            return True
        except AzureError:
            return False


# Create a single instance to reuse across the app
# This avoids creating a new connection every request
azure_service = AzureStorageService()