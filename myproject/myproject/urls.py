from django.contrib import admin
from django.urls import path
from library import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # LANDING PAGE
    path('welcome/', views.landing_page, name='landing_page'),
    # ADMIN LOGIN
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('logout/', views.admin_logout, name='logout'),
    # DASHBOARD
    path('', views.home, name='home'),
    # STUDENTS
    path('students/', views.students_list, name='students_list'),
    path('students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),
    path('students/toggle/<int:student_id>/', views.toggle_student_status, name='toggle_student_status'),
    # TEACHERS
    path('teachers/', views.teachers_list, name='teachers_list'),
    path('teachers/edit/<int:teacher_id>/', views.edit_teacher, name='edit_teacher'),
    path('teachers/delete/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),
    path('teachers/toggle/<int:teacher_id>/', views.toggle_teacher_status, name='toggle_teacher_status'),
    # BOOKS
    path('books/', views.books_list, name='books_list'),
    path('books/edit/<int:book_id>/', views.edit_book, name='edit_book'),
    path('books/delete/<int:book_id>/', views.delete_book, name='delete_book'),
    # PROFILE & REPORTS
    path('profile/', views.profile_view, name='profile'),
    path('reports/<str:report_type>/', views.reports_view, name='reports'),
    # UPLOAD
    path('upload/', views.upload_excel, name='upload_excel'),
    # LOANS
    path('loans/', views.loans_list, name='loans_list'),
    path('loans/issue/', views.issue_book, name='issue_book'),
    path('loans/return/<int:loan_id>/', views.return_book, name='return_book'),
    # RESERVATIONS
    path('reservations/', views.reservations_list, name='reservations_list'),
    path('reservations/approve/<int:reservation_id>/', views.approve_reservation, name='approve_reservation'),
    path('reservations/reject/<int:reservation_id>/', views.reject_reservation, name='reject_reservation'),
    # STUDENT PORTAL
    path('student/login/', views.student_login, name='student_login'),
    path('student/logout/', views.student_logout, name='student_logout'),
    path('student/set-password/', views.student_set_password, name='student_set_password'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/books/', views.student_books, name='student_books'),
    path('student/history/', views.student_history, name='student_history'),
    path('student/fines/', views.student_fines, name='student_fines'),
    path('student/reserve/<int:book_id>/', views.student_reserve, name='student_reserve'),
    # TEACHER PORTAL
    path('teacher/login/', views.teacher_login, name='teacher_login'),
    path('teacher/logout/', views.teacher_logout, name='teacher_logout'),
    path('teacher/set-password/', views.teacher_set_password, name='teacher_set_password'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/books/', views.teacher_books, name='teacher_books'),
    path('teacher/history/', views.teacher_history, name='teacher_history'),
    path('teacher/reserve/<int:book_id>/', views.teacher_reserve, name='teacher_reserve'),
]