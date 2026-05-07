# pdf_storage/middleware.py

import json
from django.http import JsonResponse


class JSONErrorMiddleware:
    """
    Converts ALL Django HTML error responses to JSON.
    Sits at the top of the middleware stack.
    Catches anything that returns an error status code
    with HTML content.

    This works for:
      → Unknown URLs (404)
      → Server errors (500)
      → Permission errors (403)
      → Bad requests (400)
      → Any other error Django handles before DRF
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only intercept error responses
        # that contain HTML content
        if response.status_code >= 400:
            content_type = response.get('Content-Type', '')

            if 'text/html' in content_type:
                return self._convert_to_json(response)

        return response

    def _convert_to_json(self, response):
        """Convert an HTML error response to our standard JSON format."""

        messages = {
            400: 'Bad request.',
            403: 'You do not have permission to access this.',
            404: 'The requested endpoint does not exist.',
            405: 'Method not allowed.',
            500: 'An unexpected server error occurred.',
        }

        message = messages.get(
            response.status_code,
            f'Error {response.status_code}.'
        )

        return JsonResponse(
            {
                'success': False,
                'message': message,
                'data': None,
                'errors': None,
            },
            status=response.status_code,
        )