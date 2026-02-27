from django.contrib.auth.models import User
from .models import Task
from projects.models import Project


def create_task(project, validated_data):
    """Business logic for creating a task."""
    assigned_to_id = validated_data.pop('assigned_to_id', None)
    assigned_to = None
    if assigned_to_id:
        try:
            assigned_to = User.objects.get(id=assigned_to_id)
        except User.DoesNotExist:
            pass
    return Task.objects.create(project=project, assigned_to=assigned_to, **validated_data)


def update_task(task, validated_data):
    """Business logic for updating a task."""
    assigned_to_id = validated_data.pop('assigned_to_id', 'NOT_PROVIDED')
    if assigned_to_id != 'NOT_PROVIDED':
        if assigned_to_id is None:
            task.assigned_to = None
        else:
            try:
                task.assigned_to = User.objects.get(id=assigned_to_id)
            except User.DoesNotExist:
                pass

    for field, value in validated_data.items():
        setattr(task, field, value)
    task.save()
    return task


def get_filtered_tasks(project_id=None, status=None, priority=None, search=None, ordering=None):
    """Filter, search, and order tasks."""
    qs = Task.objects.select_related('project', 'assigned_to', 'project__created_by').all()

    if project_id:
        qs = qs.filter(project_id=project_id)
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if search:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    valid_orderings = ['due_date', '-due_date', 'created_at', '-created_at', 'priority', 'status']
    if ordering in valid_orderings:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('-created_at')

    return qs
