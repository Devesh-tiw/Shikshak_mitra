from django.contrib import admin
from django.urls import path
from academy import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_page, name="login"),
    path("logout/", views.sign_out, name="logout"),
    path("auth/google/", views.google_start, name="google_start"),
    path("auth/google/callback/", views.google_callback, name="google_callback"),
    path("classes/", views.class_list, name="class_list"),
    path("classes/new/", views.create_class, name="create_class"),
    path("classes/<int:class_id>/", views.class_detail, name="class_detail"),
    path("classes/<int:class_id>/save-attendance/", views.save_attendance, name="save_attendance"),
    path("classes/<int:class_id>/students/add/", views.add_student, name="add_student"),
    path("classes/<int:class_id>/students/<int:student_id>/", views.update_student, name="update_student"),
    path("classes/<int:class_id>/insights/", views.insights, name="insights"),
    path("classes/<int:class_id>/attendance.xlsx", views.export_xlsx, name="export_xlsx"),
    path("plans/add/", views.add_plan, name="add_plan"),
    path("plans/<int:plan_id>/complete/", views.complete_plan, name="complete_plan"),
]
