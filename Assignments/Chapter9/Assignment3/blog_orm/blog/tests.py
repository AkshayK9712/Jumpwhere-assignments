from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from . import queries
from .models import Author, Post


class OrmQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = Author.objects.create(name="Alice", email="a@example.com")
        cls.bob = Author.objects.create(name="Bob", email="b@example.com")
        now = timezone.now()
        cls.a_old = Post.objects.create(author=cls.alice, title="A old", body="x", published=True)
        cls.a_draft = Post.objects.create(author=cls.alice, title="A draft", body="x", published=False)
        cls.a_new = Post.objects.create(author=cls.alice, title="A new", body="x", published=True)
        cls.b_post = Post.objects.create(author=cls.bob, title="B post", body="x", published=True)
        # created_at is auto_now_add, so set explicit distinct times via update().
        Post.objects.filter(pk=cls.a_old.pk).update(created_at=now - timedelta(days=3))
        Post.objects.filter(pk=cls.a_draft.pk).update(created_at=now - timedelta(days=2))
        Post.objects.filter(pk=cls.a_new.pk).update(created_at=now - timedelta(days=1))
        Post.objects.filter(pk=cls.b_post.pk).update(created_at=now - timedelta(days=4))

    def test_foreign_key_and_cascade(self):
        self.assertEqual(self.alice.posts.count(), 3)
        self.bob.delete()
        self.assertFalse(Post.objects.filter(title="B post").exists())

    def test_posts_by_author(self):
        titles = {p.title for p in queries.posts_by_author(self.alice)}
        self.assertEqual(titles, {"A old", "A draft", "A new"})

    def test_posts_by_author_name(self):
        self.assertEqual([p.title for p in queries.posts_by_author_name("Bob")], ["B post"])

    def test_published_newest_first(self):
        titles = [p.title for p in queries.published_newest_first()]
        self.assertEqual(titles, ["A new", "A old", "B post"])  # draft excluded

    def test_create_post(self):
        post = queries.create_post(self.bob, "New", "Body")
        self.assertIsNotNone(post.pk)
        self.assertFalse(post.published)
        self.assertEqual(post.author, self.bob)

    def test_set_published(self):
        self.assertEqual(queries.set_published(self.a_draft.pk, True), 1)
        self.a_draft.refresh_from_db()
        self.assertTrue(self.a_draft.published)

    def test_set_published_missing_id_updates_nothing(self):
        self.assertEqual(queries.set_published(99999, True), 0)
