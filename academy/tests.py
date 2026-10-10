import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AttendanceRecord, CourseClass, Student


class AttendanceFlowTests(TestCase):
    def setUp(self):
        self.teacher = get_user_model().objects.create_user(username="teacher", password="safe-password")
        self.course = CourseClass.objects.create(
            teacher=self.teacher, name="Algorithms · CSE A", branch="CSE", batch_year=2025, section="A", student_count=2
        )
        self.one = Student.objects.create(course_class=self.course, serial_number=1, name="Asha", roll_number=self.course.make_roll_number(1))
        self.two = Student.objects.create(course_class=self.course, serial_number=2, name="Ravi", roll_number=self.course.make_roll_number(2))
        self.client.force_login(self.teacher)

    def test_roll_number_uses_batch_and_section_position(self):
        self.assertEqual(self.one.roll_number, "AV.SC.U4CSE25001")
        self.course.section = "B"
        self.assertEqual(self.course.make_roll_number(1), "AV.SC.U4CSE25101")

    def test_save_attendance_creates_sql_records(self):
        response = self.client.post(
            reverse("save_attendance", args=[self.course.id]),
            data=json.dumps({"date": "2026-10-10", "slot": "Slot 1", "topic": "Graphs", "statuses": {str(self.one.id): "P", str(self.two.id): "A"}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AttendanceRecord.objects.count(), 2)
        self.assertEqual(AttendanceRecord.objects.get(student=self.one).status, "P")

    def test_teacher_cannot_save_another_teachers_class(self):
        other = get_user_model().objects.create_user(username="other", password="safe-password")
        foreign = CourseClass.objects.create(teacher=other, name="Private CSE", branch="CSE", batch_year=2025, section="A", student_count=0)
        response = self.client.post(reverse("save_attendance", args=[foreign.id]), data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 404)
