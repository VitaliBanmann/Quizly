"""Object permissions for quizzes."""
from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access only to the owner of a quiz."""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
