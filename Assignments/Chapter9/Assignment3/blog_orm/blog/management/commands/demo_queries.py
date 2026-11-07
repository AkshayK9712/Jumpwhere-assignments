from django.core.management.base import BaseCommand

from blog import queries
from blog.models import Author, Post


class Command(BaseCommand):
    help = "Seed sample data and run the four documented ORM queries, printing the results."

    def handle(self, *args, **options):
        Post.objects.all().delete()
        Author.objects.all().delete()

        alice = Author.objects.create(name="Alice", email="alice@example.com")
        bob = Author.objects.create(name="Bob", email="bob@example.com")
        alice.posts.create(title="Intro to Django", body="...", published=True)
        alice.posts.create(title="Draft: ORM tips", body="...", published=False)
        alice.posts.create(title="Migrations explained", body="...", published=True)
        bob.posts.create(title="Bob's first post", body="...", published=True)

        self.stdout.write(self.style.MIGRATE_HEADING("1. Posts by Alice"))
        for p in queries.posts_by_author(alice):
            self.stdout.write(f"  - {p.title} (published={p.published})")

        self.stdout.write(self.style.MIGRATE_HEADING("2. Published posts, newest first"))
        for p in queries.published_newest_first():
            self.stdout.write(f"  - {p.title} by {p.author.name} at {p.created_at:%H:%M:%S.%f}")

        self.stdout.write(self.style.MIGRATE_HEADING("3. Create a new post"))
        new = queries.create_post(bob, "Hello ORM", "Created via Post.objects.create()")
        self.stdout.write(f"  created id={new.pk} title={new.title!r} published={new.published}")

        self.stdout.write(self.style.MIGRATE_HEADING("4. Update the published flag"))
        updated = queries.set_published(new.pk, True)
        new.refresh_from_db()
        self.stdout.write(f"  rows updated: {updated}; published is now {new.published}")
