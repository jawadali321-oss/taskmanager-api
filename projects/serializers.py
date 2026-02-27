from rest_framework import serializers
from .models import Project
from tasks.models import Task


class ProjectSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    total_tasks = serializers.SerializerMethodField()
    incomplete_tasks = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'created_by', 'total_tasks', 'incomplete_tasks', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def get_total_tasks(self, obj):
        return obj.tasks.count()

    def get_incomplete_tasks(self, obj):
        return obj.tasks.exclude(status='done').count()


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['name', 'description']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Project name cannot be empty.")
        return value
