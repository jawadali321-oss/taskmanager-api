from rest_framework.permissions import BasePermission


class IsProjectOwner(BasePermission):
    """Only the creator of the project can delete it."""
    message = "You are not the owner of this project."

    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user
