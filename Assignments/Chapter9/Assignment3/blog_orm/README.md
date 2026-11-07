# Blog schema + Django ORM queries

## Setup
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate          # applies blog/migrations/0001_initial.py
python manage.py test             # verifies all four queries
python manage.py demo_queries     # seeds data, runs and prints all four queries
python manage.py shell            # run the queries by hand (see below)
```
If you prefer to regenerate the migration yourself: delete `blog/migrations/0001_initial.py`,
then run `python manage.py makemigrations blog` and `python manage.py migrate`.

## Schema
| Model | Fields |
|---|---|
| Author | name, email (unique), bio (optional) |
| Post | author (ForeignKey → Author, `on_delete=CASCADE`, `related_name="posts"`), title, body, published (default False), created_at (auto) |

## The four queries (`blog/queries.py`)
Open `python manage.py shell` and start with:
```python
from blog.models import Author, Post
alice = Author.objects.create(name="Alice", email="alice@example.com")
alice.posts.create(title="Intro to Django", body="...", published=True)
alice.posts.create(title="Draft: ORM tips", body="...", published=False)
```

**1. All posts by a given author**
```python
Post.objects.filter(author=alice)        # or: alice.posts.all()
Post.objects.filter(author__name="Alice")  # when you only know the name
```
Returns a QuerySet with both of Alice's posts. `author__name` follows the foreign key with a JOIN.

**2. Only published posts, newest first**
```python
Post.objects.filter(published=True).order_by("-created_at")
```
`filter(published=True)` drops drafts; the `-` prefix sorts `created_at` descending.

**3. Create a new post**
```python
Post.objects.create(author=alice, title="Hello", body="First post!")
alice.posts.create(title="Hello again", body="Author is filled in for you")
```
Both run one INSERT and return the saved Post. `published` defaults to False.

**4. Update a post's published flag**
```python
Post.objects.filter(pk=2).update(published=True)   # one UPDATE, returns rows changed (1 or 0)

post = Post.objects.get(pk=2)                      # alternative: load, modify, save
post.published = True
post.save(update_fields=["published"])
```
`.update()` is the most efficient and returns 0 instead of raising if the id doesn't exist.
`.get()` raises `Post.DoesNotExist` for a missing id.

## Notes
- No raw SQL anywhere; every query uses the ORM.
- To inspect the SQL Django generates: `print(Post.objects.filter(published=True).order_by("-created_at").query)`
