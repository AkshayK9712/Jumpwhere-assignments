"""The four required ORM queries, written as small documented functions.

Every query uses the Django ORM only (no raw SQL). Each docstring shows the
equivalent snippet to type in `python manage.py shell`.
"""
from .models import Author, Post


# 1. All posts by a given author ------------------------------------------
def posts_by_author(author):
    """Return every post written by ``author`` (an Author instance).

    Shell:
        >>> alice = Author.objects.get(name="Alice")
        >>> Post.objects.filter(author=alice)
        >>> alice.posts.all()            # same thing via the reverse relation

    ``select_related("author")`` fetches the author in the same SQL JOIN, so
    reading ``post.author`` afterwards does not trigger one query per post.
    """
    return Post.objects.filter(author=author).select_related("author")


def posts_by_author_name(name):
    """Same query when you only know the author's name (follows the FK with __).

    Shell:
        >>> Post.objects.filter(author__name="Alice")
    """
    return Post.objects.filter(author__name=name).select_related("author")


# 2. Only published posts, newest first -----------------------------------
def published_newest_first():
    """Return published posts ordered by ``created_at`` descending.

    Shell:
        >>> Post.objects.filter(published=True).order_by("-created_at")

    The leading "-" in order_by means descending, so the newest comes first.
    """
    return Post.objects.filter(published=True).order_by("-created_at")


# 3. Create a new post ----------------------------------------------------
def create_post(author, title, body, published=False):
    """Insert a new Post row and return the saved instance.

    Shell:
        >>> Post.objects.create(author=alice, title="Hello", body="First post!")
        >>> alice.posts.create(title="Hello", body="First post!")   # author filled in for you
    """
    return Post.objects.create(author=author, title=title, body=body, published=published)


# 4. Update a post's published flag --------------------------------------
def set_published(post_id, published=True):
    """Set the ``published`` flag on one post with a single UPDATE statement.

    Returns the number of rows updated (1 if the post exists, 0 if not).

    Shell:
        >>> Post.objects.filter(pk=1).update(published=True)

    Alternative (loads the object first, runs signals/validation hooks):
        >>> post = Post.objects.get(pk=1)
        >>> post.published = True
        >>> post.save(update_fields=["published"])
    """
    return Post.objects.filter(pk=post_id).update(published=published)
