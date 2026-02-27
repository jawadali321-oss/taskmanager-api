from rest_framework import serializers
from django.utils import timezone
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.StringRelatedField(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    assigned_to_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'priority',
            'project', 'project_name', 'assigned_to', 'assigned_to_id',
            'due_date', 'created_at'
        ]
        read_only_fields = ['created_at', 'project']

    def validate_due_date(self, value):
        """Phase 4: due_date cannot be in the past."""
        if value and value < timezone.now():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value

    def validate(self, attrs):
        """Phase 4: Task cannot be marked Done if not assigned to anyone."""
        status = attrs.get('status', getattr(self.instance, 'status', None))
        assigned_to_id = attrs.get('assigned_to_id', None)

        # On update, check current assignment if not being changed
        if self.instance:
            assigned = self.instance.assigned_to
            if assigned_to_id is not None:
                # Being changed in this request — validate after assignment
                if assigned_to_id is None and status == 'done':
                    raise serializers.ValidationError("Cannot mark task as Done without assigning it to a user.")
            elif assigned is None and status == 'done':
                raise serializers.ValidationError("Cannot mark task as Done without assigning it to a user.")
        else:
            # On create
            if status == 'done' and not assigned_to_id:
                raise serializers.ValidationError("Cannot mark task as Done without assigning it to a user.")

        return attrs


class TaskCreateSerializer(serializers.ModelSerializer):
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Task
        fields = ['title', 'description', 'status', 'priority', 'assigned_to_id', 'due_date']

    def validate_due_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value

    def validate(self, attrs):
        status = attrs.get('status', 'todo')
        assigned_to_id = attrs.get('assigned_to_id')
        if status == 'done' and not assigned_to_id:
            raise serializers.ValidationError("Cannot mark task as Done without assigning it to a user.")
        return attrs


class TaskUpdateSerializer(serializers.ModelSerializer):
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Task
        fields = ['title', 'description', 'status', 'priority', 'assigned_to_id', 'due_date']

    def validate_due_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value

    def validate(self, attrs):
        instance = self.instance
        new_status = attrs.get('status', instance.status)
        # Check assignment: use new value if provided, else current
        assigned_to_id = attrs.get('assigned_to_id', 'NOT_PROVIDED')
        if assigned_to_id == 'NOT_PROVIDED':
            assigned = instance.assigned_to
        else:
            assigned = assigned_to_id  # will be set in view

        if new_status == 'done' and not assigned:
            raise serializers.ValidationError("Cannot mark task as Done without assigning it to a user.")
        return attrs
