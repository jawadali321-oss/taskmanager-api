from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Task
from .serializers import TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer
from .permissions import IsAssignedUser
from .services import create_task, update_task, get_filtered_tasks
from projects.models import Project


class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'per_page'


class TaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List tasks with filters: project_id, status, priority, search, ordering"""
        tasks = get_filtered_tasks(
            project_id=request.GET.get('project_id'),
            status=request.GET.get('status'),
            priority=request.GET.get('priority'),
            search=request.GET.get('search'),
            ordering=request.GET.get('ordering'),
        )

        paginator = TaskPagination()
        page = paginator.paginate_queryset(tasks, request)
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create a task under a project"""
        project_id = request.data.get('project_id')
        if not project_id:
            return Response({'error': 'project_id is required.'}, status=400)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({'error': 'Project not found.'}, status=404)

        serializer = TaskCreateSerializer(data=request.data)
        if serializer.is_valid():
            task = create_task(project, serializer.validated_data)
            return Response(TaskSerializer(task).data, status=201)
        return Response(serializer.errors, status=400)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Task.objects.select_related('project', 'assigned_to').get(pk=pk)
        except Task.DoesNotExist:
            return None

    def get(self, request, pk):
        task = self.get_object(pk)
        if not task:
            return Response({'error': 'Task not found.'}, status=404)
        return Response(TaskSerializer(task).data)

    def put(self, request, pk):
        task = self.get_object(pk)
        if not task:
            return Response({'error': 'Task not found.'}, status=404)

        # Phase 2: Only assigned user can mark Done
        if request.data.get('status') == 'done':
            if task.assigned_to != request.user:
                return Response({'error': 'Only the assigned user can mark this task as Done.'}, status=403)

        serializer = TaskUpdateSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            updated_task = update_task(task, serializer.validated_data)
            return Response(TaskSerializer(updated_task).data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        task = self.get_object(pk)
        if not task:
            return Response({'error': 'Task not found.'}, status=404)

        # Only project owner can delete a task
        if task.project.created_by != request.user:
            return Response({'error': 'Only the project owner can delete tasks.'}, status=403)

        task.delete()
        return Response({'message': 'Task deleted successfully.'}, status=204)
