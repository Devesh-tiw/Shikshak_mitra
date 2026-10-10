import base64
import json
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, date
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .forms import CourseClassForm, StudentForm, TeachingPlanForm
from .models import AttendanceRecord, AttendanceSession, CourseClass, Student, TeachingPlan


DEMO_NAMES = [
    "Ethan", "Ava", "Mia", "Deshawn", "Priya", "Olivia", "Grace", "Henry",
    "Zoe", "Sofia", "Jaylen", "Owen", "Emma", "Marcus", "Caleb", "Nora",
    "Lucas", "Eli", "Isabella", "Maya", "Rishabh", "Liam", "Ananya", "Arjun",
    "Meera", "Karthik", "Saanvi", "Aarav", "Diya", "Vihaan", "Ishita", "Aditya",
    "Nitya", "Rahul", "Sneha", "Varun", "Kavya", "Siddharth", "Nandini", "Harsha",
]


def _demo_user(request):
    """Allow the prototype to be used immediately, without fake credentials."""
    if request.user.is_authenticated:
        return request.user
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="demo.teacher", defaults={"email": "teacher@example.com", "first_name": "Demo", "last_name": "Teacher"}
    )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    _seed_demo(user)
    return user


def _seed_demo(teacher):
    """A useful empty-state alternative: sample records show the mobile flow in the preview."""
    if CourseClass.objects.filter(teacher=teacher).exists():
        return
    cse = CourseClass.objects.create(
        teacher=teacher, name="Data Structures · CSE A", branch="CSE", batch_year=2025,
        section="A", student_count=40, colour="#7357F6"
    )
    aie = CourseClass.objects.create(
        teacher=teacher, name="Python Lab · AIE B", branch="AIE", batch_year=2025,
        section="B", student_count=28, colour="#0D9E8B"
    )
    students = [Student(course_class=cse, name=name, roll_number=cse.make_roll_number(i), serial_number=i)
                for i, name in enumerate(DEMO_NAMES, 1)]
    students += [Student(course_class=aie, name=f"Student {i}", roll_number=aie.make_roll_number(i), serial_number=i)
                 for i in range(1, 29)]
    Student.objects.bulk_create(students)
    # A few past sessions make the analytics page meaningful on first open.
    cse_students = list(cse.students.all())
    for day, slot, present_until in [(date(2026, 10, 6), "Slot 2", 35), (date(2026, 10, 7), "Slot 2", 32), (date(2026, 10, 8), "Slot 2", 38)]:
        session = AttendanceSession.objects.create(course_class=cse, date=day, slot=slot, topic="Trees & traversal")
        AttendanceRecord.objects.bulk_create([
            AttendanceRecord(session=session, student=s, status="P" if s.serial_number <= present_until else "A")
            for s in cse_students
        ])
    TeachingPlan.objects.bulk_create([
        TeachingPlan(course_class=cse, kind="TEST", title="Unit 2 quiz", due_date=date(2026, 10, 14)),
        TeachingPlan(course_class=cse, kind="ASSIGNMENT", title="Stack implementation", due_date=date(2026, 10, 17)),
        TeachingPlan(course_class=aie, kind="TEST", title="Python lab evaluation", due_date=date(2026, 10, 15)),
    ])


def teacher_required(view):
    def wrapped(request, *args, **kwargs):
        _demo_user(request)
        return view(request, *args, **kwargs)
    return wrapped


def _owned_class(request, class_id):
    return get_object_or_404(CourseClass, pk=class_id, teacher=request.user)


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return timezone.localdate()


def _class_stats(course_class):
    sessions = course_class.attendance_sessions.all()
    session_count = sessions.count()
    student_rows = []
    records = AttendanceRecord.objects.filter(session__course_class=course_class).values("student_id", "status")
    by_student = {}
    for row in records:
        by_student.setdefault(row["student_id"], {"P": 0, "A": 0, "L": 0, "E": 0})[row["status"]] += 1
    for student in course_class.students.filter(active=True):
        count = by_student.get(student.id, {})
        attended = count.get("P", 0) + count.get("L", 0) + count.get("E", 0)
        rate = round((attended / session_count) * 100) if session_count else 0
        student_rows.append({"student": student, "attended": attended, "rate": rate})
    present_records = AttendanceRecord.objects.filter(session__course_class=course_class, status__in=["P", "L", "E"]).count()
    total_possible = course_class.students.filter(active=True).count() * session_count
    return {
        "sessions": session_count,
        "students": course_class.students.filter(active=True).count(),
        "overall_rate": round((present_records / total_possible) * 100) if total_possible else 0,
        "student_rows": student_rows,
        "at_risk": [row for row in student_rows if session_count and row["rate"] < 75],
    }


@teacher_required
def dashboard(request):
    classes = list(CourseClass.objects.filter(teacher=request.user, is_archived=False).prefetch_related("students"))
    plans = TeachingPlan.objects.filter(course_class__teacher=request.user, completed=False).select_related("course_class")[:5]
    total_students = Student.objects.filter(course_class__teacher=request.user, active=True).count()
    sessions_today = AttendanceSession.objects.filter(course_class__teacher=request.user, date=timezone.localdate()).count()
    class_summaries = []
    for item in classes:
        stats = _class_stats(item)
        class_summaries.append({"course_class": item, "stats": stats})
    plan_form = TeachingPlanForm()
    plan_form.fields["course_class"].queryset = CourseClass.objects.filter(teacher=request.user, is_archived=False)
    return render(request, "academy/dashboard.html", {
        "classes": classes, "class_summaries": class_summaries, "plans": plans,
        "total_students": total_students, "sessions_today": sessions_today,
        "plan_form": plan_form,
    })


@teacher_required
def class_list(request):
    classes = CourseClass.objects.filter(teacher=request.user).prefetch_related("students", "attendance_sessions")
    cards = [{"course_class": item, "stats": _class_stats(item)} for item in classes]
    return render(request, "academy/classes.html", {"cards": cards})


@teacher_required
def create_class(request):
    if request.method == "POST":
        form = CourseClassForm(request.POST)
        if form.is_valid():
            course_class = form.save(commit=False)
            course_class.teacher = request.user
            course_class.colour = request.POST.get("colour", "#7357F6")
            course_class.save()
            # Build editable placeholders; the teacher replaces these names in the roster.
            Student.objects.bulk_create([
                Student(course_class=course_class, serial_number=i, roll_number=course_class.make_roll_number(i), name=f"Student {i}")
                for i in range(1, course_class.student_count + 1)
            ])
            messages.success(request, f"{course_class.name} is ready. Add names whenever you are ready.")
            return redirect("class_detail", class_id=course_class.id)
    else:
        form = CourseClassForm(initial={"batch_year": timezone.localdate().year, "section": "A", "colour": "#7357F6"})
    return render(request, "academy/create_class.html", {"form": form})


@teacher_required
def class_detail(request, class_id):
    course_class = _owned_class(request, class_id)
    marked_date = _parse_date(request.GET.get("date"))
    slot = (request.GET.get("slot") or "Slot 1").strip()[:60]
    session = AttendanceSession.objects.filter(course_class=course_class, date=marked_date, slot=slot).prefetch_related("records").first()
    status_by_student = {record.student_id: record.status for record in session.records.all()} if session else {}
    students = list(course_class.students.filter(active=True))
    student_rows = [{"student": student, "status": status_by_student.get(student.id, "U")} for student in students]
    return render(request, "academy/attendance.html", {
        "course_class": course_class, "students": students, "student_rows": student_rows, "selected_date": marked_date,
        "selected_slot": slot, "session": session, "status_by_student": status_by_student,
        "stats": _class_stats(course_class), "student_form": StudentForm(),
    })


@teacher_required
@require_POST
def save_attendance(request, class_id):
    course_class = _owned_class(request, class_id)
    try:
        payload = json.loads(request.body)
        marked_date = _parse_date(payload.get("date"))
        slot = str(payload.get("slot") or "Slot 1").strip()[:60]
        topic = str(payload.get("topic") or "").strip()[:160]
        statuses = payload.get("statuses", {})
        if not isinstance(statuses, dict):
            raise ValueError("statuses must be an object")
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"ok": False, "message": "Please check the attendance data and try again."}, status=400)

    valid_students = {str(pk) for pk in course_class.students.filter(active=True).values_list("id", flat=True)}
    invalid = set(statuses) - valid_students
    if invalid or any(v not in {"P", "A", "L", "E"} for v in statuses.values()):
        return JsonResponse({"ok": False, "message": "One or more student marks are invalid."}, status=400)

    with transaction.atomic():
        session, _ = AttendanceSession.objects.update_or_create(
            course_class=course_class, date=marked_date, slot=slot,
            defaults={"topic": topic},
        )
        records = [
            AttendanceRecord(session=session, student_id=int(student_id), status=status)
            for student_id, status in statuses.items()
        ]
        AttendanceRecord.objects.bulk_create(records, update_conflicts=True, unique_fields=["session", "student"], update_fields=["status", "marked_at"])
    present = sum(1 for value in statuses.values() if value in {"P", "L", "E"})
    return JsonResponse({"ok": True, "message": "Attendance saved", "session_id": session.id, "present": present, "total": len(valid_students)})


@teacher_required
@require_POST
def add_student(request, class_id):
    course_class = _owned_class(request, class_id)
    form = StudentForm(request.POST)
    if form.is_valid():
        serial = (course_class.students.aggregate(max_serial=Count("id"))["max_serial"] or 0) + 1
        student = form.save(commit=False)
        student.course_class = course_class
        student.serial_number = serial
        student.roll_number = course_class.make_roll_number(serial)
        student.save()
        course_class.student_count = course_class.students.filter(active=True).count()
        course_class.save(update_fields=["student_count"])
        messages.success(request, f"{student.name} added as {student.roll_number}.")
    else:
        messages.error(request, "Please enter a student name.")
    return redirect("class_detail", class_id=class_id)


@teacher_required
@require_POST
def update_student(request, class_id, student_id):
    course_class = _owned_class(request, class_id)
    student = get_object_or_404(Student, pk=student_id, course_class=course_class)
    name = request.POST.get("name", "").strip()
    if name:
        student.name = name[:120]
        student.save(update_fields=["name"])
        messages.success(request, "Student name updated.")
    return redirect("class_detail", class_id=class_id)


@teacher_required
def insights(request, class_id):
    course_class = _owned_class(request, class_id)
    stats = _class_stats(course_class)
    sessions = course_class.attendance_sessions.all().prefetch_related("records")[:10]
    trend = []
    total_students = stats["students"] or 1
    for item in reversed(list(sessions)):
        present = sum(1 for r in item.records.all() if r.status in {"P", "L", "E"})
        trend.append({"label": item.date.strftime("%d %b"), "rate": round(present / total_students * 100), "present": present})
    return render(request, "academy/insights.html", {"course_class": course_class, "stats": stats, "trend": trend})


@teacher_required
@require_POST
def add_plan(request):
    form = TeachingPlanForm(request.POST)
    form.fields["course_class"].queryset = CourseClass.objects.filter(teacher=request.user, is_archived=False)
    if form.is_valid():
        form.save()
        messages.success(request, "Added to your teaching plan.")
    else:
        messages.error(request, "Please complete the plan details.")
    return redirect("dashboard")


@teacher_required
@require_POST
def complete_plan(request, plan_id):
    plan = get_object_or_404(TeachingPlan, pk=plan_id, course_class__teacher=request.user)
    plan.completed = True
    plan.save(update_fields=["completed"])
    return redirect("dashboard")


@teacher_required
@require_GET
def export_xlsx(request, class_id):
    course_class = _owned_class(request, class_id)
    sessions = list(course_class.attendance_sessions.all().order_by("date", "slot"))
    students = list(course_class.students.filter(active=True))
    records = AttendanceRecord.objects.filter(session__in=sessions).values("session_id", "student_id", "status")
    record_map = {(r["session_id"], r["student_id"]): r["status"] for r in records}

    book = Workbook()
    sheet = book.active
    sheet.title = "Attendance"
    sheet.freeze_panes = "C2"
    sheet.append([f"{course_class.name} — Attendance register"])
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(4, len(sessions) + 4))
    sheet["A1"].font = Font(bold=True, color="FFFFFF", size=14)
    sheet["A1"].fill = PatternFill("solid", fgColor="5B42D7")
    sheet["A1"].alignment = Alignment(horizontal="center")
    headers = ["#", "Roll number", "Student name"] + [f"{s.date.strftime('%d %b')}\n{s.slot}" for s in sessions] + ["Attendance %"]
    sheet.append(headers)
    for cell in sheet[2]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="7357F6")
        cell.alignment = Alignment(wrap_text=True, horizontal="center")
    for i, student in enumerate(students, 1):
        marks = [record_map.get((session.id, student.id), "—") for session in sessions]
        attended = sum(1 for mark in marks if mark in {"P", "L", "E"})
        percentage = round((attended / len(sessions) * 100), 1) if sessions else 0
        sheet.append([i, student.roll_number, student.name] + marks + [percentage])
    sheet.column_dimensions["A"].width = 6
    sheet.column_dimensions["B"].width = 25
    sheet.column_dimensions["C"].width = 25
    for col in range(4, len(headers) + 1):
        sheet.column_dimensions[chr(64 + min(col, 26))].width = 13
    for row in sheet.iter_rows(min_row=3):
        for cell in row:
            cell.alignment = Alignment(horizontal="center" if cell.column != 3 else "left")
    stream = BytesIO()
    book.save(stream)
    filename = f"{course_class.branch}_{course_class.section}_attendance.xlsx"
    response = HttpResponse(stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "academy/login.html")


def google_start(request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
        messages.info(request, "Google OAuth keys are not configured in this preview. A secure demo workspace has been opened instead.")
        return redirect("dashboard")
    state = secrets.token_urlsafe(24)
    request.session["google_oauth_state"] = state
    parameters = urllib.parse.urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID, "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code", "scope": "openid email profile", "state": state, "access_type": "online",
    })
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{parameters}")


def google_callback(request):
    if request.GET.get("state") != request.session.pop("google_oauth_state", None):
        messages.error(request, "Google sign-in could not be verified. Please try again.")
        return redirect("login")
    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google sign-in was cancelled.")
        return redirect("login")
    try:
        body = urllib.parse.urlencode({"code": code, "client_id": settings.GOOGLE_CLIENT_ID, "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI, "grant_type": "authorization_code"}).encode()
        token = json.loads(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=body, method="POST"), timeout=10).read())
        profile = json.loads(urllib.request.urlopen(urllib.request.Request("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {token['access_token']}"}), timeout=10).read())
        User = get_user_model()
        user, _ = User.objects.get_or_create(username=f"google:{profile['sub']}", defaults={"email": profile.get("email", ""), "first_name": profile.get("given_name", ""), "last_name": profile.get("family_name", "")})
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("dashboard")
    except Exception:
        messages.error(request, "Google sign-in did not complete. Verify your OAuth redirect URI and credentials.")
        return redirect("login")


def sign_out(request):
    logout(request)
    return redirect("login")
