# documents/permissions.py

from rest_framework.permissions import BasePermission


class IsDocumentOwner(BasePermission):
    """
    Object-level permission.
    Users can only access their own documents.
    """

    message = 'You do not have permission to access this document.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user