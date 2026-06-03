from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta

# Create your models here.
#model for library members
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    member_id = models.CharField(max_length=20, unique=True)
    phone = models.IntegerField()
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    joined_date = models.DateField(auto_now_add=True)
    address = models.TextField()

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.member_id})"
    
#model for books in the library
class Book(models.Model):
    CATEGORY_CHOICES = [
        ('Fiction', 'Fiction'),
        ('Non-Fiction', 'Non-Fiction'),
        ('Science', 'Science'),
        ('History', 'History'),
        ('Technology', 'Technology'),
        ('Matematics', 'Mathematics'),
        ('Other', 'Other'),
    ]
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    total_copies = models.IntegerField(default=1)
    available_copies = models.IntegerField(default=1)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    description = models.TextField(blank=True)
    added_date = models.DateField(auto_now_add=True)
    isbn = models.CharField(max_length=20, unique=True)
    barcode_image = models.ImageField(upload_to='barcodes/', null=True, blank=True)

    def __str__(self):
        return f"{self.title} by {self.author}"
    
    def is_available(self):
        return self.available_copies > 0

#model for issued books
class IssuedBook(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(default=date.today() + timedelta(days=14))
    returned = models.BooleanField(default=False)


    def is_overdue(self):
        return date.today() > self.due_date and not self.returned

    def days_overdue(self):
        if self.is_overdue():
            return (date.today() - self.due_date).days
        return 0

    def __str__(self):
        return f"{self.book.title} issued to {self.member.user.get_full_name()}"
    
# model for returned books
class ReturnedBook(models.Model):
    issued_book = models.OneToOneField(IssuedBook, on_delete=models.CASCADE)
    return_date = models.DateField(auto_now_add=True)
    condition = models.CharField(max_length=50, choices=[
        ('Good', 'Good'),
        ('Damaged', 'Damaged'),
        ('Lost', 'Lost'),], default='Good')
    
    def __str__(self):
        return f"Returned: {self.issued_book.book.title} "
    
# model for fine
class Fine(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    paid = models.BooleanField(default=False)
    issued_book = models.ForeignKey(IssuedBook, on_delete=models.CASCADE)

    FINE_PER_DAY = 2

    def calculate_fine(self):
        days = self.issued_book.days_overdue()
        self.amount = days * self.FINE_PER_DAY
        self.save()

    def __str__(self):
        return f" Fine Rs. {self.amount} - {self.member}"
    
# model for reservation
class Reservation(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    reservation_date = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.member} reserved {self.book.title}"
                                                         