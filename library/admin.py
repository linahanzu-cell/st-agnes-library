from django.contrib import admin
from .models import Student, Teacher, Book, BookCopy, Loan, Reservation

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
    list_display = ('book_id', 'title', 'author', 'grade', 'total_copies')
    search_fields = ('title', 'author', 'book_id')

@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ('copy_number', 'book', 'is_available')
    search_fields = ('copy_number',)
    list_filter = ('is_available',)

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('book', 'student', 'teacher', 'date_borrowed', 'date_due', 'date_returned')
    list_filter = ('date_due', 'date_returned')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('book', 'student', 'teacher', 'status', 'date_reserved')
    list_filter = ('status',)