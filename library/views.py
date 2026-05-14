from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from .models import Student, Teacher, Book, BookCopy, Loan, Reservation
from django.db.models import Sum, Q
from django.contrib import messages
from django.utils import timezone
from functools import wraps
from datetime import date, datetime
import pandas as pd

# ============================================================
# DECORATORS
# ============================================================

def student_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('student_id'):
            return redirect('student_login')
        return view_func(request, *args, **kwargs)
    return wrapper

def teacher_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('teacher_portal_id'):
            return redirect('teacher_login')
        return view_func(request, *args, **kwargs)
    return wrapper

# ============================================================
# LANDING & AUTH
# ============================================================

def welcome(request):
    return render(request, 'login/welcome.html')

def landing_page(request):
    return render(request, 'login/home.html')

class StaffLoginView(LoginView):
    template_name = 'login/sign_in.html'

def admin_logout(request):
    logout(request)
    return redirect('login')

# ============================================================
# ADMIN DASHBOARD
# ============================================================

@login_required
def home(request):
    active_loans = Loan.objects.filter(date_returned__isnull=True)

    active_fines = sum(loan.calculate_fine() for loan in active_loans if loan.student)

    returned_unpaid_fines = Loan.objects.filter(
        student__isnull=False,
        date_returned__isnull=False,
        fine_amount__gt=0,
        fine_paid=False,
    ).aggregate(total=Sum('fine_amount'))['total'] or 0

    total_fines = active_fines + returned_unpaid_fines

    try:
        available = BookCopy.objects.filter(is_available=True).count()
    except:
        available = 0

    # ✅ FIX: days_overdue is a @property on the model — never assign to it
    overdue_loans = []
    for loan in active_loans:
        if loan.student and loan.calculate_fine() > 0:
            overdue_loans.append(loan)

    pending_reservations = Reservation.objects.filter(status='pending').count()

    context = {
        'total_finances': total_fines,
        'total_students': Student.objects.count(),
        'total_teachers': Teacher.objects.count(),
        'available_books': available,
        'issued_books': active_loans.count(),
        'overdue_loans': overdue_loans,
        'pending_reservations': pending_reservations,
    }
    return render(request, 'dashboard/main_view.html', context)

# ============================================================
# ADMIN PROFILE
# ============================================================

@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        if new_password:
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match!")
                return redirect('profile')
            if len(new_password) < 6:
                messages.error(request, "Password must be at least 6 characters!")
                return redirect('profile')
            user.set_password(new_password)
            messages.success(request, "Profile and password updated! Please log in again.")
        else:
            messages.success(request, "Profile updated successfully!")
        user.save()
        return redirect('profile')
    return render(request, 'dashboard/profile.html', {'user': request.user})

# ============================================================
# STUDENTS - ADMIN
# ============================================================

@login_required
def students_list(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        admission_number = request.POST.get('admission_number', '').strip()
        grade = request.POST.get('grade', '').strip()
        stream = request.POST.get('stream', '').strip()
        if not all([first_name, last_name, admission_number, grade, stream]):
            messages.error(request, "All fields are required.")
        elif Student.objects.filter(admission_number=admission_number).exists():
            messages.error(request, f"Admission number {admission_number} already exists.")
        else:
            Student.objects.create(
                first_name=first_name, last_name=last_name,
                admission_number=admission_number, grade=grade, stream=stream,
            )
            messages.success(request, f"Student {first_name} {last_name} added successfully!")
        return redirect('students_list')
    students = Student.objects.all().order_by('grade', 'stream', 'last_name')
    return render(request, 'dashboard/students_list.html', {'students': students})

@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.first_name = request.POST.get('first_name', '').strip()
        student.last_name = request.POST.get('last_name', '').strip()
        student.admission_number = request.POST.get('admission_number', '').strip()
        student.grade = request.POST.get('grade', '').strip()
        student.stream = request.POST.get('stream', '').strip()
        if request.POST.get('reset_password'):
            student.is_first_login = True
            student.password = ''
            messages.info(request, f"{student.first_name}'s password reset. They will set a new one on next login.")
        student.save()
        messages.success(request, f"Student {student.first_name} {student.last_name} updated successfully!")
        return redirect('students_list')
    return render(request, 'dashboard/edit_student.html', {'student': student})

@login_required
def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        name = f"{student.first_name} {student.last_name}"
        student.delete()
        messages.success(request, f"Student {name} deleted successfully.")
    return redirect('students_list')

@login_required
def toggle_student_status(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    student.status = 'Inactive' if student.status == 'Active' else 'Active'
    student.save()
    messages.info(request, f"{student.first_name}'s status updated to {student.status}.")
    return redirect('students_list')

# ============================================================
# TEACHERS - ADMIN
# ============================================================

@login_required
def teachers_list(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        teacher_id = request.POST.get('teacher_id', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        if not all([first_name, last_name, teacher_id, email, phone_number]):
            messages.error(request, "All fields are required.")
        elif Teacher.objects.filter(teacher_id=teacher_id).exists():
            messages.error(request, f"Teacher ID {teacher_id} already exists.")
        else:
            Teacher.objects.create(
                first_name=first_name, last_name=last_name,
                teacher_id=teacher_id, email=email, phone_number=phone_number,
            )
            messages.success(request, f"Teacher {first_name} {last_name} added successfully!")
        return redirect('teachers_list')
    teachers = Teacher.objects.all().order_by('last_name')
    return render(request, 'dashboard/teachers_list.html', {'teachers': teachers})

@login_required
def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    if request.method == 'POST':
        teacher.first_name = request.POST.get('first_name', '').strip()
        teacher.last_name = request.POST.get('last_name', '').strip()
        teacher.teacher_id = request.POST.get('teacher_id', '').strip()
        teacher.email = request.POST.get('email', '').strip()
        teacher.phone_number = request.POST.get('phone_number', '').strip()
        if request.POST.get('reset_password'):
            teacher.is_first_login = True
            teacher.password = ''
            messages.info(request, f"{teacher.first_name}'s password reset. They will set a new one on next login.")
        teacher.save()
        messages.success(request, f"Teacher {teacher.first_name} {teacher.last_name} updated successfully!")
        return redirect('teachers_list')
    return render(request, 'dashboard/edit_teacher.html', {'teacher': teacher})

@login_required
def delete_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    if request.method == 'POST':
        name = f"{teacher.first_name} {teacher.last_name}"
        teacher.delete()
        messages.success(request, f"Teacher {name} deleted successfully.")
    return redirect('teachers_list')

@login_required
def toggle_teacher_status(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    teacher.status = 'Inactive' if teacher.status == 'Active' else 'Active'
    teacher.save()
    messages.info(request, f"{teacher.first_name}'s status updated to {teacher.status}.")
    return redirect('teachers_list')

# ============================================================
# BOOKS - ADMIN
# ============================================================

@login_required
def books_list(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        author = request.POST.get('author', '').strip()
        subject = request.POST.get('subject', '').strip()
        category = request.POST.get('category', '').strip()
        publisher = request.POST.get('publisher', '').strip()
        grade = request.POST.get('grade', '').strip()
        total_copies = request.POST.get('total_copies', '1').strip()
        if not all([title, author, subject, category, publisher, grade]):
            messages.error(request, "All fields are required.")
        else:
            existing = Book.objects.filter(
                title__iexact=title,
                grade__iexact=grade
            ).first()
            if existing:
                existing.total_copies = int(total_copies)
                existing.author = author
                existing.subject = subject
                existing.category = category
                existing.publisher = publisher
                existing.save()
                messages.success(request, f"Book '{title}' already exists — updated to {total_copies} copies!")
            else:
                Book.objects.create(
                    title=title, author=author, subject=subject, category=category,
                    publisher=publisher, grade=grade, total_copies=int(total_copies),
                )
                messages.success(request, f"Book '{title}' added successfully!")
        return redirect('books_list')
    books = Book.objects.all().order_by('book_id')
    book_data = []
    for book in books:
        try:
            available = BookCopy.objects.filter(book=book, is_available=True).count()
        except:
            available = 0
        book_data.append({'book': book, 'available': available})
    return render(request, 'dashboard/books_list.html', {'book_data': book_data})

@login_required
def edit_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        book.title = request.POST.get('title', '').strip()
        book.author = request.POST.get('author', '').strip()
        book.subject = request.POST.get('subject', '').strip()
        book.category = request.POST.get('category', '').strip()
        book.publisher = request.POST.get('publisher', '').strip()
        book.grade = request.POST.get('grade', '').strip()
        book.total_copies = int(request.POST.get('total_copies', '1'))
        book.save()
        messages.success(request, f"Book updated successfully!")
        return redirect('books_list')
    return render(request, 'dashboard/edit_book.html', {'book': book})

@login_required
def delete_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f"Book '{title}' deleted successfully.")
    return redirect('books_list')

# ============================================================
# EXCEL UPLOAD
# ============================================================

@login_required
def upload_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        file = request.FILES['excel_file']
        try:
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip().str.lower()
            df.rename(columns={
                'book name': 'title',
                'book_name': 'title',
                'quantity': 'total_copies',
                'qty': 'total_copies',
            }, inplace=True)

            if 'admission_number' in df.columns:
                required = ['first_name', 'last_name', 'admission_number', 'grade', 'stream']
                missing = [c for c in required if c not in df.columns]
                if missing:
                    messages.error(request, f"Missing columns: {', '.join(missing)}")
                    return redirect('students_list')
                count = 0
                for _, row in df.iterrows():
                    if pd.isna(row['admission_number']):
                        continue
                    Student.objects.update_or_create(
                        admission_number=str(row['admission_number']).strip(),
                        defaults={
                            'first_name': str(row['first_name']).strip(),
                            'last_name': str(row['last_name']).strip(),
                            'grade': str(int(float(str(row['grade'])))),
                            'stream': str(row['stream']).strip().upper(),
                        }
                    )
                    count += 1
                messages.success(request, f"{count} students imported successfully.")
                return redirect('students_list')

            elif 'teacher_id' in df.columns:
                required = ['first_name', 'last_name', 'teacher_id', 'email', 'phone_number']
                missing = [c for c in required if c not in df.columns]
                if missing:
                    messages.error(request, f"Missing columns: {', '.join(missing)}")
                    return redirect('teachers_list')
                count = 0
                for _, row in df.iterrows():
                    if pd.isna(row['teacher_id']):
                        continue
                    Teacher.objects.update_or_create(
                        teacher_id=str(row['teacher_id']).strip(),
                        defaults={
                            'first_name': str(row['first_name']).strip(),
                            'last_name': str(row['last_name']).strip(),
                            'email': str(row['email']).strip(),
                            'phone_number': str(row['phone_number']).strip(),
                        }
                    )
                    count += 1
                messages.success(request, f"{count} teachers imported successfully.")
                return redirect('teachers_list')

            elif 'title' in df.columns:
                required = ['title', 'author', 'subject', 'category', 'publisher', 'grade', 'total_copies']
                missing = [c for c in required if c not in df.columns]
                if missing:
                    messages.error(request, f"Missing columns: {', '.join(missing)}")
                    return redirect('books_list')
                count = 0
                for _, row in df.iterrows():
                    if pd.isna(row['title']):
                        continue
                    raw_grade = str(row['grade']).strip()
                    raw_grade = raw_grade.replace('Grade ', '').replace('grade ', '').strip()
                    try:
                        raw_grade = str(int(float(raw_grade)))
                    except:
                        raw_grade = raw_grade.capitalize()
                    try:
                        copies = int(float(str(row['total_copies'])))
                    except:
                        copies = 1
                    Book.objects.update_or_create(
                        title=str(row['title']).strip(),
                        grade=raw_grade,
                        defaults={
                            'author': str(row['author']).strip(),
                            'subject': str(row['subject']).strip(),
                            'category': str(row['category']).strip().lower(),
                            'publisher': str(row['publisher']).strip(),
                            'total_copies': copies,
                        }
                    )
                    count += 1
                messages.success(request, f"{count} books imported/updated successfully.")
                return redirect('books_list')
            else:
                messages.error(request, "Could not detect file type. Check your column names.")
        except Exception as e:
            messages.error(request, f"Error reading file: {str(e)}")
    return redirect('books_list')

# ============================================================
# REPORTS - ADMIN
# ============================================================

@login_required
def reports_view(request, report_type):
    context = {'report_type': report_type}

    if report_type == 'available_books':
        books = Book.objects.all()
        book_data = []
        for book in books:
            try:
                available = BookCopy.objects.filter(book=book, is_available=True).count()
            except:
                available = 0
            book_data.append({'book': book, 'available': available})
        context['book_data'] = book_data

    elif report_type == 'issued_books':
        loans = Loan.objects.all().select_related(
            'book', 'student', 'teacher'
        ).order_by('-date_borrowed')
        search_book = request.GET.get('search_book', '').strip()
        borrower_type = request.GET.get('borrower_type', '').strip()
        grade_filter = request.GET.get('grade', '').strip()
        start_date = request.GET.get('start_date', '').strip()
        end_date = request.GET.get('end_date', '').strip()
        status_filter = request.GET.get('status', '').strip()
        if search_book:
            loans = loans.filter(book__title__icontains=search_book)
        if borrower_type == 'student':
            loans = loans.filter(student__isnull=False, teacher__isnull=True)
        elif borrower_type == 'teacher':
            loans = loans.filter(teacher__isnull=False, student__isnull=True)
        if grade_filter:
            loans = loans.filter(
                Q(student__grade=grade_filter) | Q(book__grade=grade_filter)
            )
        if start_date:
            loans = loans.filter(date_borrowed__gte=start_date)
        if end_date:
            loans = loans.filter(date_borrowed__lte=end_date)
        if status_filter == 'issued':
            loans = loans.filter(date_returned__isnull=True)
        elif status_filter == 'returned':
            loans = loans.filter(date_returned__isnull=False)
        context['loans'] = loans
        context['search_book'] = search_book
        context['borrower_type'] = borrower_type
        context['grade_filter'] = grade_filter
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['status_filter'] = status_filter
        context['total_results'] = loans.count()

    elif report_type == 'student_report':
        context['loans'] = Loan.objects.filter(
            student__isnull=False
        ).select_related('student', 'book').order_by('-date_borrowed')

    elif report_type == 'teacher_report':
        context['loans'] = Loan.objects.filter(
            teacher__isnull=False
        ).select_related('teacher', 'book').order_by('-date_borrowed')

    elif report_type == 'fines_report':
        grade_filter = request.GET.get('grade', '').strip()
        stream_filter = request.GET.get('stream', '').strip()
        month_filter = request.GET.get('month', '').strip()
        year_filter = request.GET.get('year', '').strip()
        paid_filter = request.GET.get('paid_status', '').strip()

        active_loans = Loan.objects.filter(
            student__isnull=False,
            date_returned__isnull=True,
            fine_paid=False,
        ).select_related('student', 'book').order_by('student__last_name')

        returned_unpaid = Loan.objects.filter(
            student__isnull=False,
            date_returned__isnull=False,
            fine_amount__gt=0,
            fine_paid=False,
        ).select_related('student', 'book').order_by('student__last_name')

        paid_fines = Loan.objects.filter(
            student__isnull=False,
            fine_paid=True,
        ).select_related('student', 'book').order_by('-fine_paid_date')

        if grade_filter:
            active_loans = active_loans.filter(student__grade=grade_filter)
            returned_unpaid = returned_unpaid.filter(student__grade=grade_filter)
            paid_fines = paid_fines.filter(student__grade=grade_filter)
        if stream_filter:
            active_loans = active_loans.filter(student__stream=stream_filter)
            returned_unpaid = returned_unpaid.filter(student__stream=stream_filter)
            paid_fines = paid_fines.filter(student__stream=stream_filter)
        if month_filter:
            active_loans = active_loans.filter(date_borrowed__month=month_filter)
            returned_unpaid = returned_unpaid.filter(date_borrowed__month=month_filter)
            paid_fines = paid_fines.filter(date_borrowed__month=month_filter)
        if year_filter:
            active_loans = active_loans.filter(date_borrowed__year=year_filter)
            returned_unpaid = returned_unpaid.filter(date_borrowed__year=year_filter)
            paid_fines = paid_fines.filter(date_borrowed__year=year_filter)

        active_fines_data = []
        for loan in active_loans:
            fine = loan.calculate_fine()
            if fine > 0:
                active_fines_data.append({
                    'loan': loan,
                    'fine': fine,
                    'days_overdue': loan.days_overdue,
                    'status': 'Active Loan',
                })
        for loan in returned_unpaid:
            active_fines_data.append({
                'loan': loan,
                'fine': loan.fine_amount,
                'days_overdue': 0,
                'status': 'Book Returned',
            })

        total_unpaid = sum(item['fine'] for item in active_fines_data)
        total_paid = paid_fines.aggregate(total=Sum('fine_amount'))['total'] or 0

        context['fines_data'] = active_fines_data
        context['paid_fines'] = paid_fines
        context['total_unpaid'] = total_unpaid
        context['total_paid'] = total_paid
        context['grade_filter'] = grade_filter
        context['stream_filter'] = stream_filter
        context['month_filter'] = month_filter
        context['year_filter'] = year_filter
        context['paid_filter'] = paid_filter

    return render(request, 'dashboard/reports.html', context)

# ============================================================
# MARK FINE AS PAID
# ============================================================

@login_required
def mark_fine_paid(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if request.method == 'POST':
        if loan.fine_amount == 0:
            loan.fine_amount = loan.calculate_fine()
        loan.fine_paid = True
        loan.fine_paid_date = timezone.now().date()
        loan.save()
        name = f"{loan.student.first_name} {loan.student.last_name}"
        messages.success(
            request,
            f"Fine of KSH {loan.fine_amount} for {name} marked as PAID! ✅"
        )
    return redirect(request.META.get('HTTP_REFERER', '/reports/fines_report/'))

@login_required
def toggle_status(request, person_type, person_id):
    if person_type == 'student':
        obj = get_object_or_404(Student, id=person_id)
    else:
        obj = get_object_or_404(Teacher, id=person_id)
    obj.status = 'Inactive' if obj.status == 'Active' else 'Active'
    obj.save()
    messages.info(request, f"Status updated to {obj.status}")
    return redirect(f'{person_type}s_list')

# ============================================================
# LOANS - ADMIN
# ============================================================

@login_required
def loans_list(request):
    active_loans = Loan.objects.filter(
        date_returned__isnull=True
    ).select_related('book', 'student', 'teacher', 'copy').order_by('-date_borrowed')
    returned_loans = Loan.objects.filter(
        date_returned__isnull=False
    ).select_related('book', 'student', 'teacher', 'copy').order_by('-date_returned')
    return render(request, 'dashboard/loans_list.html', {
        'active_loans': active_loans,
        'returned_loans': returned_loans,
        'today': date.today(),
    })

@login_required
def issue_book(request):
    if request.method == 'POST':
        book_id = request.POST.get('book')
        copy_id = request.POST.get('copy')
        student_id = request.POST.get('student')
        teacher_id = request.POST.get('teacher')
        date_due = request.POST.get('date_due')
        borrower_type = request.POST.get('borrower_type')

        if not book_id or not date_due:
            messages.error(request, "Book and due date are required.")
            return redirect('issue_book')

        # ✅ FIX: Validate due date is not before today
        try:
            date_due_parsed = datetime.strptime(date_due, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "❌ Invalid date format. Please use the date picker.")
            return redirect('issue_book')

        if date_due_parsed < date.today():
            messages.error(
                request,
                f"❌ Due date ({date_due_parsed}) cannot be before today ({date.today()})! "
                f"Please select today or a future date."
            )
            return redirect('issue_book')

        book = get_object_or_404(Book, id=book_id)
        copy = None
        if copy_id:
            copy = get_object_or_404(BookCopy, id=copy_id)
            if not copy.is_available:
                messages.error(request, f"Copy {copy.copy_number} is not available.")
                return redirect('issue_book')

        if borrower_type == 'student' and student_id:
            student = get_object_or_404(Student, id=student_id)
            if Loan.objects.filter(
                book=book, student=student, date_returned__isnull=True
            ).exists():
                messages.error(request, f"{student.first_name} already has this book.")
                return redirect('issue_book')
            Loan.objects.create(book=book, copy=copy, student=student, date_due=date_due)
            if copy:
                copy.is_available = False
                copy.save()
            copy_info = f"copy {copy.copy_number}" if copy else ""
            messages.success(request, f"'{book.title}' {copy_info} issued to {student.first_name} {student.last_name}!")
        elif borrower_type == 'teacher' and teacher_id:
            teacher = get_object_or_404(Teacher, id=teacher_id)
            if Loan.objects.filter(
                book=book, teacher=teacher, date_returned__isnull=True
            ).exists():
                messages.error(request, f"{teacher.first_name} already has this book.")
                return redirect('issue_book')
            Loan.objects.create(book=book, copy=copy, teacher=teacher, date_due=date_due)
            if copy:
                copy.is_available = False
                copy.save()
            copy_info = f"copy {copy.copy_number}" if copy else ""
            messages.success(request, f"'{book.title}' {copy_info} issued to {teacher.first_name} {teacher.last_name}!")
        else:
            messages.error(request, "Please select a student or teacher.")
            return redirect('issue_book')
        return redirect('loans_list')

    books = Book.objects.all().order_by('book_id')
    students = Student.objects.filter(status='Active').order_by('last_name')
    teachers = Teacher.objects.filter(status='Active').order_by('last_name')
    copies = BookCopy.objects.filter(
        is_available=True
    ).select_related('book').order_by('book__title', 'copy_number')
    return render(request, 'dashboard/issue_book.html', {
        'books': books,
        'students': students,
        'teachers': teachers,
        'copies': copies,
        'today': date.today(),
    })

@login_required
def edit_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if request.method == 'POST':
        new_due_date_str = request.POST.get('date_due', '').strip()
        try:
            new_due_date = datetime.strptime(new_due_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "❌ Invalid date format. Please use the date picker.")
            return render(request, 'dashboard/edit_loan.html', {'loan': loan})

        if new_due_date < loan.date_borrowed:
            messages.error(
                request,
                f"❌ Due date ({new_due_date}) cannot be before the borrowing date ({loan.date_borrowed})!"
            )
            return render(request, 'dashboard/edit_loan.html', {'loan': loan})

        loan.date_due = new_due_date
        loan.save()
        messages.success(request, "Loan due date updated successfully!")
        return redirect('loans_list')
    return render(request, 'dashboard/edit_loan.html', {'loan': loan})

@login_required
def return_book(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if request.method == 'POST':
        return_date_str = request.POST.get('return_date', '').strip()

        if return_date_str:
            try:
                return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "❌ Invalid date format. Please use the date picker.")
                return redirect('loans_list')

            if return_date < loan.date_borrowed:
                messages.error(
                    request,
                    f"❌ Return date ({return_date}) cannot be before the borrowing date ({loan.date_borrowed})! Please enter a correct date."
                )
                return redirect('loans_list')

            if return_date > timezone.now().date():
                messages.error(
                    request,
                    f"❌ Return date ({return_date}) cannot be in the future!"
                )
                return redirect('loans_list')
        else:
            return_date = timezone.now().date()

        fine = loan.calculate_fine()
        loan.fine_amount = fine
        loan.date_returned = return_date
        loan.save()

        try:
            if loan.copy:
                loan.copy.is_available = True
                loan.copy.save()
        except:
            pass

        name = f"{loan.student.first_name} {loan.student.last_name}" if loan.student \
            else f"{loan.teacher.first_name} {loan.teacher.last_name}"

        if fine > 0:
            messages.warning(request, f"'{loan.book.title}' returned by {name}. Fine: KSH {fine} — Please collect payment.")
        else:
            messages.success(request, f"'{loan.book.title}' returned by {name} successfully!")

    return redirect('loans_list')

@login_required
def delete_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if request.method == 'POST':
        loan.delete()
        messages.success(request, "Loan record deleted successfully.")
    return redirect('loans_list')

# ============================================================
# RESERVATIONS - ADMIN
# ============================================================

@login_required
def reservations_list(request):
    pending = Reservation.objects.filter(status='pending').select_related(
        'book', 'student', 'teacher').order_by('-date_reserved')
    approved = Reservation.objects.filter(status='approved').select_related(
        'book', 'student', 'teacher').order_by('-date_reserved')
    rejected = Reservation.objects.filter(status='rejected').select_related(
        'book', 'student', 'teacher').order_by('-date_reserved')
    return render(request, 'dashboard/reservations.html', {
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
    })

@login_required
def approve_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.status = 'approved'
    reservation.save()
    person = reservation.student or reservation.teacher
    messages.success(request, f"Reservation for '{reservation.book.title}' by {person} approved!")
    return redirect('reservations_list')

@login_required
def reject_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.status = 'rejected'
    reservation.save()
    person = reservation.student or reservation.teacher
    messages.warning(request, f"Reservation for '{reservation.book.title}' by {person} rejected.")
    return redirect('reservations_list')

# ============================================================
# STUDENT PORTAL
# ============================================================

def student_login(request):
    if request.method == 'POST':
        admission_number = request.POST.get('admission_number', '').strip()
        password = request.POST.get('password', '').strip()
        try:
            student = Student.objects.get(admission_number=admission_number)
            if student.is_first_login:
                request.session['pending_student_id'] = student.id
                return redirect('student_set_password')
            if student.check_password(password):
                request.session['student_id'] = student.id
                return redirect('student_dashboard')
            else:
                return render(request, 'student/login.html',
                    {'error': 'Wrong password. Try again.'})
        except Student.DoesNotExist:
            return render(request, 'student/login.html',
                {'error': 'Admission number not found.'})
    return render(request, 'student/login.html')

def student_set_password(request):
    student_id = request.session.get('pending_student_id')
    if not student_id:
        return redirect('student_login')
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        password = request.POST.get('password', '').strip()
        confirm = request.POST.get('confirm_password', '').strip()
        if len(password) < 6:
            return render(request, 'student/set_password.html', {
                'error': 'Password must be at least 6 characters.',
                'student': student})
        if password != confirm:
            return render(request, 'student/set_password.html', {
                'error': 'Passwords do not match.',
                'student': student})
        student.set_password(password)
        student.is_first_login = False
        student.save()
        request.session['student_id'] = student.id
        del request.session['pending_student_id']
        return redirect('student_dashboard')
    return render(request, 'student/set_password.html', {'student': student})

def student_logout(request):
    if 'student_id' in request.session:
        del request.session['student_id']
    return redirect('student_login')

@student_login_required
def student_dashboard(request):
    student = get_object_or_404(Student, id=request.session['student_id'])
    active_loans = Loan.objects.filter(student=student, date_returned__isnull=True)
    total_fines = sum(loan.calculate_fine() for loan in active_loans)
    reservations = Reservation.objects.filter(student=student).order_by('-date_reserved')[:5]
    return render(request, 'student/dashboard.html', {
        'student': student,
        'active_loans': active_loans,
        'total_fines': total_fines,
        'reservations': reservations,
        'books_borrowed': active_loans.count(),
    })

@student_login_required
def student_books(request):
    student = get_object_or_404(Student, id=request.session['student_id'])
    query = request.GET.get('q', '')
    books = Book.objects.all()
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(subject__icontains=query))
    book_data = []
    for book in books:
        try:
            available = BookCopy.objects.filter(book=book, is_available=True).count()
        except:
            available = book.total_copies - Loan.objects.filter(
                book=book, date_returned__isnull=True).count()
        already_reserved = Reservation.objects.filter(
            book=book, student=student, status='pending').exists()
        already_borrowed = Loan.objects.filter(
            book=book, student=student, date_returned__isnull=True).exists()
        book_data.append({
            'book': book,
            'available': available,
            'already_reserved': already_reserved,
            'already_borrowed': already_borrowed,
        })
    return render(request, 'student/books.html', {
        'book_data': book_data, 'query': query, 'student': student})

@student_login_required
def student_history(request):
    student = get_object_or_404(Student, id=request.session['student_id'])
    loans = Loan.objects.filter(
        student=student).select_related('book').order_by('-date_borrowed')
    return render(request, 'student/history.html', {'loans': loans, 'student': student})

@student_login_required
def student_fines(request):
    student = get_object_or_404(Student, id=request.session['student_id'])
    active_loans = Loan.objects.filter(student=student, date_returned__isnull=True)
    fine_data = []
    total = 0
    for loan in active_loans:
        fine = loan.calculate_fine()
        if fine > 0:
            days = (timezone.now().date() - loan.date_due).days
            fine_data.append({'loan': loan, 'fine': fine, 'days': days})
            total += fine
    return render(request, 'student/fines.html', {
        'fine_data': fine_data, 'total': total, 'student': student})

@student_login_required
def student_reserve(request, book_id):
    student = get_object_or_404(Student, id=request.session['student_id'])
    book = get_object_or_404(Book, id=book_id)
    if Reservation.objects.filter(book=book, student=student, status='pending').exists():
        messages.warning(request, f"You already have a pending reservation for '{book.title}'.")
    else:
        Reservation.objects.create(book=book, student=student)
        messages.success(request, f"Reservation for '{book.title}' submitted! The librarian will approve it shortly.")
    return redirect('student_books')

@student_login_required
def student_profile(request):
    student = get_object_or_404(Student, id=request.session['student_id'])
    if request.method == 'POST':
        student.first_name = request.POST.get('first_name', student.first_name).strip()
        student.last_name = request.POST.get('last_name', student.last_name).strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        if new_password:
            if len(new_password) < 6:
                return render(request, 'student/profile.html', {
                    'error': 'Password must be at least 6 characters.',
                    'student': student})
            if new_password != confirm_password:
                return render(request, 'student/profile.html', {
                    'error': 'Passwords do not match.',
                    'student': student})
            student.set_password(new_password)
            messages.success(request, "Password updated successfully!")
        else:
            messages.success(request, "Profile updated successfully!")
        student.save()
        return redirect('student_profile')
    return render(request, 'student/profile.html', {'student': student})

@student_login_required
def student_report(request):
    student = get_object_or_404(Student, id=request.session['student_id'])
    loans = Loan.objects.filter(
        student=student).select_related('book').order_by('-date_borrowed')
    total_fines = sum(
        loan.fine_amount if loan.date_returned else loan.calculate_fine()
        for loan in loans
    )
    return render(request, 'student/report.html', {
        'student': student,
        'loans': loans,
        'total_fines': total_fines,
    })

# ============================================================
# TEACHER PORTAL
# ============================================================

def teacher_login(request):
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id', '').strip()
        password = request.POST.get('password', '').strip()
        try:
            teacher = Teacher.objects.get(teacher_id=teacher_id)
            if teacher.is_first_login:
                request.session['pending_teacher_id'] = teacher.id
                return redirect('teacher_set_password')
            if teacher.check_password(password):
                request.session['teacher_portal_id'] = teacher.id
                return redirect('teacher_dashboard')
            else:
                return render(request, 'teacher/login.html',
                    {'error': 'Wrong password. Try again.'})
        except Teacher.DoesNotExist:
            return render(request, 'teacher/login.html',
                {'error': 'Teacher ID not found.'})
    return render(request, 'teacher/login.html')

def teacher_set_password(request):
    teacher_id = request.session.get('pending_teacher_id')
    if not teacher_id:
        return redirect('teacher_login')
    teacher = get_object_or_404(Teacher, id=teacher_id)
    if request.method == 'POST':
        password = request.POST.get('password', '').strip()
        confirm = request.POST.get('confirm_password', '').strip()
        if len(password) < 6:
            return render(request, 'teacher/set_password.html', {
                'error': 'Password must be at least 6 characters.',
                'teacher': teacher})
        if password != confirm:
            return render(request, 'teacher/set_password.html', {
                'error': 'Passwords do not match.',
                'teacher': teacher})
        teacher.set_password(password)
        teacher.is_first_login = False
        teacher.save()
        request.session['teacher_portal_id'] = teacher.id
        del request.session['pending_teacher_id']
        return redirect('teacher_dashboard')
    return render(request, 'teacher/set_password.html', {'teacher': teacher})

def teacher_logout(request):
    if 'teacher_portal_id' in request.session:
        del request.session['teacher_portal_id']
    return redirect('teacher_login')

@teacher_login_required
def teacher_dashboard(request):
    teacher = get_object_or_404(Teacher, id=request.session['teacher_portal_id'])
    active_loans = Loan.objects.filter(teacher=teacher, date_returned__isnull=True)
    reservations = Reservation.objects.filter(
        teacher=teacher).order_by('-date_reserved')[:5]
    return render(request, 'teacher/dashboard.html', {
        'teacher': teacher,
        'active_loans': active_loans,
        'reservations': reservations,
        'books_borrowed': active_loans.count(),
    })

@teacher_login_required
def teacher_books(request):
    teacher = get_object_or_404(Teacher, id=request.session['teacher_portal_id'])
    query = request.GET.get('q', '')
    books = Book.objects.all()
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(subject__icontains=query))
    book_data = []
    for book in books:
        try:
            available = BookCopy.objects.filter(book=book, is_available=True).count()
        except:
            available = book.total_copies - Loan.objects.filter(
                book=book, date_returned__isnull=True).count()
        already_reserved = Reservation.objects.filter(
            book=book, teacher=teacher, status='pending').exists()
        book_data.append({
            'book': book,
            'available': available,
            'already_reserved': already_reserved,
        })
    return render(request, 'teacher/books.html', {
        'book_data': book_data, 'query': query, 'teacher': teacher})

@teacher_login_required
def teacher_history(request):
    teacher = get_object_or_404(Teacher, id=request.session['teacher_portal_id'])
    loans = Loan.objects.filter(
        teacher=teacher).select_related('book').order_by('-date_borrowed')
    return render(request, 'teacher/history.html', {'loans': loans, 'teacher': teacher})

@teacher_login_required
def teacher_reserve(request, book_id):
    teacher = get_object_or_404(Teacher, id=request.session['teacher_portal_id'])
    book = get_object_or_404(Book, id=book_id)
    if Reservation.objects.filter(book=book, teacher=teacher, status='pending').exists():
        messages.warning(request, f"You already have a pending reservation for '{book.title}'.")
    else:
        Reservation.objects.create(book=book, teacher=teacher)
        messages.success(request, f"Reservation for '{book.title}' submitted! The librarian will approve it shortly.")
    return redirect('teacher_books')

@teacher_login_required
def teacher_profile(request):
    teacher = get_object_or_404(Teacher, id=request.session['teacher_portal_id'])
    if request.method == 'POST':
        teacher.first_name = request.POST.get('first_name', teacher.first_name).strip()
        teacher.last_name = request.POST.get('last_name', teacher.last_name).strip()
        teacher.email = request.POST.get('email', teacher.email).strip()
        teacher.phone_number = request.POST.get('phone_number', teacher.phone_number).strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        if new_password:
            if len(new_password) < 6:
                return render(request, 'teacher/profile.html', {
                    'error': 'Password must be at least 6 characters.',
                    'teacher': teacher})
            if new_password != confirm_password:
                return render(request, 'teacher/profile.html', {
                    'error': 'Passwords do not match.',
                    'teacher': teacher})
            teacher.set_password(new_password)
            messages.success(request, "Password updated successfully!")
        else:
            messages.success(request, "Profile updated successfully!")
        teacher.save()
        return redirect('teacher_profile')
    return render(request, 'teacher/profile.html', {'teacher': teacher})

@teacher_login_required
def teacher_report(request):
    teacher = get_object_or_404(Teacher, id=request.session['teacher_portal_id'])
    loans = Loan.objects.filter(
        teacher=teacher).select_related('book').order_by('-date_borrowed')
    active_count = loans.filter(date_returned__isnull=True).count()
    returned_count = loans.filter(date_returned__isnull=False).count()
    return render(request, 'teacher/report.html', {
        'teacher': teacher,
        'loans': loans,
        'active_count': active_count,
        'returned_count': returned_count,
    })