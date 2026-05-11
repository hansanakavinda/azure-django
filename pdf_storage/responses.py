# pdf_storage/responses.py

from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """
    Standard success response.
    Use this everywhere instead of Response() directly.
    """
    return Response({
        'success': True,
        'message': message,
        'data': data,
        'errors': None,
    }, status=status_code)


def error_response(errors=None, message="Something went wrong", data=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Standard error response.
    Use this everywhere instead of Response() directly.
    """
    return Response({
        'success': False,
        'message': message,
        'data': data,
        'errors': errors,
    }, status=status_code)