from django import forms
from django.utils import timezone
from .models import CourseClass, Student, TeachingPlan


class CourseClassForm(forms.ModelForm):
    class Meta:
        model = CourseClass
        fields = ["name", "branch", "batch_year", "section", "student_count", "colour"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Data Structures · CSE A"}),
            "branch": forms.Select(),
            "batch_year": forms.NumberInput(attrs={"min": 2020, "max": 2040, "value": timezone.now().year}),
            "section": forms.Select(choices=[(x, f"Section {x}") for x in "ABCDEF"]),
            "student_count": forms.NumberInput(attrs={"min": 1, "max": 240, "placeholder": "e.g. 54"}),
            "colour": forms.HiddenInput(),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["name", "email"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Student name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Optional university email"}),
        }


class TeachingPlanForm(forms.ModelForm):
    class Meta:
        model = TeachingPlan
        fields = ["course_class", "kind", "title", "due_date", "details"]
        widgets = {
            "course_class": forms.Select(),
            "kind": forms.Select(),
            "title": forms.TextInput(attrs={"placeholder": "e.g. Unit 2 quiz"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "details": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note for yourself"}),
        }
