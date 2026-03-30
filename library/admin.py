from django.contrib import admin
from .models import Student, Teacher, Book, Loan

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('admission_number', 'first_name', 'last_name', 'grade', 'stream')
    search_fields = ('admission_number', 'last_name')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'first_name', 'last_name', 'email')
    search_fields = ('teacher_id', 'last_name')

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'total_copies')
    search_fields = ('title', 'isbn')

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('book', 'student', 'teacher', 'date_borrowed', 'date_due', 'date_returned')
    list_filter = ('date_due', 'date_returned')