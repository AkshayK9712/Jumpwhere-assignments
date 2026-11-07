# Django CRUD Task Manager

## Setup
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
Open http://127.0.0.1:8000/

## Routes
| URL | View | Purpose |
|---|---|---|
| `/` | TaskListView | List all tasks |
| `/tasks/new/` | TaskCreateView | Create |
| `/tasks/<id>/` | TaskDetailView | Read one |
| `/tasks/<id>/edit/` | TaskUpdateView | Update |
| `/tasks/<id>/delete/` | TaskDeleteView | Delete (confirm page) |

## Tests
```bash
python manage.py test
```
