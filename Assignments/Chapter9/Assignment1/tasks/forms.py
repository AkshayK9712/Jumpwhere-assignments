from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "completed"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "What needs doing?"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }
