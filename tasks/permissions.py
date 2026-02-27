from rest_framework.permissions import BasePermission


class IsAssignedUser(BasePermission):
    """Only the assigned user can mark a task as Done."""
    message = "Only the assigned user can mark this task as Done."

    def has_object_permission(self, request, view, obj):
        # Allow all actions except marking done
        if request.data.get('status') == 'done':
            return obj.assigned_to == request.user
        return True
