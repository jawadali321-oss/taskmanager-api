from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Project
from .serializers import ProjectSerializer, ProjectCreateSerializer
from .services import create_project, can_delete_project, has_incomplete_tasks


class ProjectListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all projects (authenticated users see all projects)"""
        projects = Project.objects.select_related('created_by').prefetch_related('tasks').filter(created_by=request.user)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new project"""
        serializer = ProjectCreateSerializer(data=request.data)
        if serializer.is_valid():
            project = create_project(request.user, serializer.validated_data)
            return Response(ProjectSerializer(project).data, status=201)
        return Response(serializer.errors, status=400)


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Project.objects.select_related('created_by').prefetch_related('tasks').get(pk=pk)
        except Project.DoesNotExist:
            return None

    def get(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response({'error': 'Project not found.'}, status=404)
        return Response(ProjectSerializer(project).data)

    def put(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response({'error': 'Project not found.'}, status=404)

        if not can_delete_project(request.user, project):
            return Response({'error': 'Only the project owner can update this project.'}, status=403)

        serializer = ProjectCreateSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ProjectSerializer(project).data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response({'error': 'Project not found.'}, status=404)

        # Phase 2: Only owner can delete
        if not can_delete_project(request.user, project):
            return Response({'error': 'Only the project owner can delete this project.'}, status=403)

        # Phase 4: Cannot delete if incomplete tasks exist
        if has_incomplete_tasks(project):
            return Response({'error': 'Cannot delete project with incomplete tasks. Complete or remove all tasks first.'}, status=400)

        project.delete()
        return Response({'message': 'Project deleted successfully.'}, status=204)
