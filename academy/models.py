from django.conf import settings
from django.db import models
from django.utils import timezone

class CourseClass(models.Model):
    """A class/section owned by one teacher."""

    class Branch(models.TextChoices):
        AIE = "AIE", "AIE · Artificial Intelligence Engineering"
        CSE = "CSE", "CSE · Computer Science Engineering"
        CCE = "CCE", "CCE · Computer & Communication Engineering"
        AIDS = "AIDS", "AIDS · AI & Data Science"
        QC = "QC", "QC · Quantum Computing"
        ECE = "ECE", "ECE · Electronics & Communication Engineering"
        CUSTOM = "CUSTOM", "Custom programme"

    SCHOOL_PREFIX = {
        "AIE": "AV.SC.U4", "CSE": "AV.SC.U4",
        "CCE": "AV.EN.U4", "AIDS": "AV.EN.U4",
        "QC": "AV.EN.U4", "ECE": "AV.EN.U4", "CUSTOM": "AV.U4",
    }

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teaching_classes")
    name = models.CharField(max_length=100)
    branch = models.CharField(max_length=10, choices=Branch.choices)
    batch_year = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=1, default="A")
    student_count = models.PositiveSmallIntegerField(default=0)
    colour = models.CharField(max_length=7, default="#6D4AFF")
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["branch", "batch_year", "section", "name"]
        constraints = [
            models.UniqueConstraint(fields=["teacher", "name"], name="unique_class_name_per_teacher"),
        ]

    def __str__(self):
        return self.name

    @property
    def roll_prefix(self):
        return self.SCHOOL_PREFIX.get(self.branch, "AV.U4") + self.branch

    @property
    def batch_suffix(self):
        return str(self.batch_year)[-2:]

    def make_roll_number(self, sequence):
        """Amrita-style preview: batch last two + section position + student sequence.
        A / first student in 2025 -> 25001; B / first -> 25101.
        """
        section_position = max(0, ord((self.section or "A").upper()[0]) - ord("A"))
        return f"{self.roll_prefix}{self.batch_suffix}{section_position}{sequence:02d}"


class Student(models.Model):
    course_class = models.ForeignKey(CourseClass, on_delete=models.CASCADE, related_name="students")
    roll_number = models.CharField(max_length=40)
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    serial_number = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["serial_number", "name"]
        constraints = [
            models.UniqueConstraint(fields=["course_class", "roll_number"], name="unique_roll_per_class"),
        ]
        indexes = [models.Index(fields=["course_class", "active"])]

    def __str__(self):
        return f"{self.roll_number} — {self.name}"


class AttendanceSession(models.Model):
    course_class = models.ForeignKey(CourseClass, on_delete=models.CASCADE, related_name="attendance_sessions")
    date = models.DateField(default=timezone.localdate)
    slot = models.CharField(max_length=60, default="Slot 1")
    topic = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "slot"]
        constraints = [
            models.UniqueConstraint(fields=["course_class", "date", "slot"], name="unique_class_date_slot"),
        ]
        indexes = [models.Index(fields=["course_class", "date"])]

    def __str__(self):
        return f"{self.course_class} · {self.date} · {self.slot}"


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "P", "Present"
        ABSENT = "A", "Absent"
        LATE = "L", "Late"
        EXCUSED = "E", "Excused"

    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="records")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.ABSENT)
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "student"], name="unique_student_per_attendance_session"),
        ]
        indexes = [models.Index(fields=["student", "status"])]


class TeachingPlan(models.Model):
    class Kind(models.TextChoices):
        TEST = "TEST", "Test", "test"
        ASSIGNMENT = "ASSIGNMENT", "Assignment", "assignment"
        NOTE = "NOTE", "Reminder"

    course_class = models.ForeignKey(CourseClass, on_delete=models.CASCADE, related_name="plans")
    title = models.CharField(max_length=140)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.NOTE)
    due_date = models.DateField()
    details = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["completed", "due_date"]
