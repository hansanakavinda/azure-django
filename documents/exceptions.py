# documents/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

# Get a logger for tracking errors
logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for all API errors.
    Always returns JSON regardless of the error type.

    exc     = the exception that was raised
    context = info about the view that raised it
    """

    # First let DRF handle what it knows about
    # This handles things like 400, 401, 403, 404, 405
    response = exception_handler(exc, context)

    if response is not None:
        # DRF handled it — reformat the response to be consistent
        # By default DRF returns different formats for different errors
        # We want everything to look the same

        error_data = {
            'error': {
                'status_code': response.status_code,
                'message': _get_error_message(response),
                'details': response.data,
            }
        }

        response.data = error_data
        return response

    # If response is None, DRF did not handle it
    # This means it is an unexpected server error (500)
    # Log it so you can debug later
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            'view': context.get('view'),
            'request': context.get('request'),
        }
    )

    return Response(
        {
            'error': {
                'status_code': 500,
                'message': 'An unexpected error occurred. Please try again later.',
                'details': None,
                # Notice: we do NOT return str(exc) here
                # Never expose internal error details to clients
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def _get_error_message(response):
    """
    Extract a clean human readable message from the response.
    DRF stores error info in different places depending on the error.
    This normalizes it.
    """

    status_code = response.status_code

    # Map status codes to friendly messages
    default_messages = {
        400: 'Invalid request data.',
        401: 'Authentication required. Please login.',
        403: 'You do not have permission to perform this action.',
        404: 'The requested resource was not found.',
        405: 'This HTTP method is not allowed on this endpoint.',
        408: 'Request timed out.',
        429: 'Too many requests. Please slow down.',
        500: 'Internal server error.',
    }

    return default_messages.get(status_code, f'Error {status_code}')