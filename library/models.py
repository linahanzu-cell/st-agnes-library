from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password as django_check_password

class Student(models.Model):
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    admission_number = models.CharField(max_length=50, unique=True)
    grade = models.CharField(max_length=20)
    stream = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    password = models.CharField(max_length=255, blank=True, default='')
    is_first_login = models.BooleanField(default=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return django_check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Teacher(models.Model):
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    teacher_id = models.CharField(max_length=50, unique=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    department = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    password = models.CharField(max_length=255, blank=True, default='')
    is_first_login = models.BooleanField(default=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return django_check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Book(models.Model):
    CATEGORY_CHOICES = [
        ('textbook', 'Textbook'),
        ('storybook', 'Story Book'),
        ('atlas', 'Atlas'),
        ('dictionary', 'Dictionary'),
        ('encyclopedia', 'Encyclopedia'),
        ('novel', 'Novel'),
        ('reference', 'Reference Book'),
        ('science', 'Science Book'),
        ('religious', 'Religious Book'),
        ('activity', 'Activity Book'),
    ]

    book_id = models.CharField(max_length=50, unique=True, blank=True)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='textbook')
    publisher = models.CharField(max_length=200, default='')
    isbn = models.CharField(max_length=50, unique=True)
    grade = models.CharField(max_length=20)
    total_copies = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        if not self.book_id:
            last = Book.objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.book_id = f"BK-{next_num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Loan(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True)
    date_borrowed = models.DateField(auto_now_add=True)
    date_due = models.DateField()
    date_returned = models.DateField(null=True, blank=True)
    quantity = models.IntegerField(default=1)

    def calculate_fine(self):
        if not self.date_returned and timezone.now().date() > self.date_due:
            days_late = (timezone.now().date() - self.date_due).days
            return days_late * 50
        return 0

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True)
    date_reserved = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        person = self.student or self.teacher
        return f"{person} - {self.book.title}"