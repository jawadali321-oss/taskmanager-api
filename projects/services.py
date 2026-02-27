from .models import Project


def create_project(user, validated_data):
    """Business logic for creating a project."""
    return Project.objects.create(created_by=user, **validated_data)


def can_delete_project(user, project):
    """Only the owner can delete a project."""
    return project.created_by == user


def has_incomplete_tasks(project):
    """Check if project has any incomplete tasks."""
    return project.tasks.exclude(status='done').exists()
