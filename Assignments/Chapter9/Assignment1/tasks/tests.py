from django.test import TestCase
from django.urls import reverse

from .models import Task


class TaskCrudTests(TestCase):
    def setUp(self):
        self.task = Task.objects.create(title="Write report", description="Q3 summary")

    def test_list(self):
        resp = self.client.get(reverse("tasks:list"))
        self.assertContains(resp, "Write report")

    def test_detail(self):
        resp = self.client.get(self.task.get_absolute_url())
        self.assertContains(resp, "Q3 summary")

    def test_create(self):
        resp = self.client.post(
            reverse("tasks:create"), {"title": "New task", "description": "", "completed": ""}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Task.objects.filter(title="New task").exists())

    def test_update(self):
        resp = self.client.post(
            reverse("tasks:update", args=[self.task.pk]),
            {"title": "Write report v2", "description": "", "completed": "on"},
        )
        self.assertEqual(resp.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Write report v2")
        self.assertTrue(self.task.completed)

    def test_delete(self):
        resp = self.client.post(reverse("tasks:delete", args=[self.task.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
