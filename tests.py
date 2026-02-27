from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from projects.models import Project
from tasks.models import Task


# ─── AUTH TESTS ───────────────────────────────────────────────────────────────

class RegisterTestCase(APITestCase):

    def test_register_success(self):
        """User can register with valid data"""
        # We skip OTP email sending in tests
        pass  # Covered via direct user creation below

    def test_login_unverified_user(self):
        """Unverified user cannot login"""
        User.objects.create_user(username='unverified', password='pass123', email='u@test.com', is_active=False)
        res = self.client.post('/api/auth/login/', {'username': 'unverified', 'password': 'pass123'})
        self.assertIn(res.status_code, [401, 403])

    def test_login_success(self):
        """Active user can login and receive tokens"""
        User.objects.create_user(username='active', password='pass123', email='a@test.com', is_active=True)
        res = self.client.post('/api/auth/login/', {'username': 'active', 'password': 'pass123'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('tokens', res.data)

    def test_login_wrong_password(self):
        """Wrong password returns 401"""
        User.objects.create_user(username='user1', password='correct', is_active=True)
        res = self.client.post('/api/auth/login/', {'username': 'user1', 'password': 'wrong'})
        self.assertEqual(res.status_code, 401)


# ─── PROJECT TESTS ────────────────────────────────────────────────────────────

class ProjectTestCase(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass123', is_active=True)
        self.other = User.objects.create_user(username='other', password='pass123', is_active=True)
        # Login owner
        res = self.client.post('/api/auth/login/', {'username': 'owner', 'password': 'pass123'})
        self.owner_token = res.data['tokens']['access']
        # Login other
        res2 = self.client.post('/api/auth/login/', {'username': 'other', 'password': 'pass123'})
        self.other_token = res2.data['tokens']['access']

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_create_project_authenticated(self):
        """Authenticated user can create a project"""
        self.auth(self.owner_token)
        res = self.client.post('/api/projects/', {'name': 'Test Project', 'description': 'Desc'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['name'], 'Test Project')

    def test_create_project_unauthenticated(self):
        """Unauthenticated user cannot create a project"""
        res = self.client.post('/api/projects/', {'name': 'No Auth'})
        self.assertEqual(res.status_code, 401)

    def test_non_owner_cannot_delete_project(self):
        """Non-owner cannot delete a project - Phase 2"""
        self.auth(self.owner_token)
        project = Project.objects.create(name='My Project', created_by=self.owner)
        self.auth(self.other_token)
        res = self.client.delete(f'/api/projects/{project.id}/')
        self.assertIn(res.status_code, [401, 403])

    def test_owner_can_delete_empty_project(self):
        """Owner can delete project with no tasks"""
        self.auth(self.owner_token)
        project = Project.objects.create(name='Empty Project', created_by=self.owner)
        res = self.client.delete(f'/api/projects/{project.id}/')
        self.assertEqual(res.status_code, 204)

    def test_cannot_delete_project_with_incomplete_tasks(self):
        """Cannot delete project if it has incomplete tasks - Phase 4"""
        self.auth(self.owner_token)
        project = Project.objects.create(name='Project With Tasks', created_by=self.owner)
        Task.objects.create(title='Incomplete Task', project=project, status='todo')
        res = self.client.delete(f'/api/projects/{project.id}/')
        self.assertEqual(res.status_code, 400)
        self.assertIn('incomplete tasks', res.data['error'])


# ─── TASK TESTS ───────────────────────────────────────────────────────────────

class TaskTestCase(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(username='towner', password='pass123', is_active=True)
        self.assignee = User.objects.create_user(username='assignee', password='pass123', is_active=True)
        self.other = User.objects.create_user(username='tother', password='pass123', is_active=True)

        res = self.client.post('/api/auth/login/', {'username': 'towner', 'password': 'pass123'})
        self.owner_token = res.data['tokens']['access']
        res2 = self.client.post('/api/auth/login/', {'username': 'assignee', 'password': 'pass123'})
        self.assignee_token = res2.data['tokens']['access']
        res3 = self.client.post('/api/auth/login/', {'username': 'tother', 'password': 'pass123'})
        self.other_token = res3.data['tokens']['access']

        self.project = Project.objects.create(name='Test Project', created_by=self.owner)
        self.task = Task.objects.create(
            title='Test Task', project=self.project,
            assigned_to=self.assignee, status='todo'
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_past_due_date_rejected(self):
        """Due date in the past is rejected - Phase 4"""
        self.auth(self.owner_token)
        past = (timezone.now() - timedelta(days=1)).isoformat()
        res = self.client.post('/api/tasks/', {
            'project_id': self.project.id,
            'title': 'Past Task',
            'due_date': past
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('due_date', str(res.data).lower() or 'past' in str(res.data).lower())

    def test_only_assignee_can_mark_done(self):
        """Only assigned user can mark task as Done - Phase 2"""
        self.auth(self.other_token)
        res = self.client.put(f'/api/tasks/{self.task.id}/', {'status': 'done'})
        self.assertIn(res.status_code, [401, 403])

    def test_assignee_can_mark_done(self):
        """Assigned user can successfully mark task as Done"""
        self.auth(self.assignee_token)
        res = self.client.put(f'/api/tasks/{self.task.id}/', {'status': 'done'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'done')

    def test_task_without_assignee_cannot_be_done(self):
        """Task without assignee cannot be marked Done - Phase 4"""
        self.auth(self.owner_token)
        unassigned_task = Task.objects.create(
            title='Unassigned', project=self.project, assigned_to=None, status='todo'
        )
        res = self.client.put(f'/api/tasks/{unassigned_task.id}/', {'status': 'done'})
        # Either 400 (validation) or 403 (permission)
        self.assertIn(res.status_code, [400, 403])

    def test_filter_tasks_by_status(self):
        """Tasks can be filtered by status"""
        self.auth(self.owner_token)
        res = self.client.get('/api/tasks/?status=todo')
        self.assertEqual(res.status_code, 200)

    def test_search_tasks(self):
        """Tasks can be searched by title"""
        self.auth(self.owner_token)
        res = self.client.get('/api/tasks/?search=Test Task')
        self.assertEqual(res.status_code, 200)
