from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import *
import random
from datetime import date, timedelta
from .utils import send_sms, get_sms_message, generate_book_barcode

# Create your views here.

# Register View
def register_view(request):
    if request.method =='POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        username = request.POST['username']
        phone = request.POST['phone']
        address = request.POST['address']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        # check password match
        if password1 != password2:
            messages.error(request, 'Password did not match!')
            return redirect('register')
        
        #check username already exists or not
        if User.objects.filter(username=username).exists():
            messages.error(request,'Username already taken!')
            return redirect('register')
        
        #Create User
        user = User.objects.create_user(
            username = username,
            password = password1,
            email = email,
            first_name = first_name,
            last_name = last_name,
            
        )

        #member id genrate
        year = str(date.today().year)
        member_id = 'MEM'+ year[2:] + str(random.randint(1000,9999))

        #create member profile
        Member.objects.create(
            user = user,
            member_id = member_id,
            phone= phone,
            address = address
        )

        messages.success(request,f'Account created! your member id is {member_id}. Please login')
        return redirect('login')
    
    return render(request, 'library/register.html')

# login view

def login_view(request):
    if request.method =='POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back {user.get_full_name()}!')

            #check if admin or member
            if user.is_staff:
                return redirect('admin_dashboard')
            else:
                return redirect('member_dashboard')
        else:
            messages.error(request,'Invalid username or password!')
            return redirect('login')
    
    return render(request,'library/login.html')

#logout view;
def logout_view(request):
    logout(request)
    messages.success(request,'Logged out successfully!')
    return redirect('login')

#dashboards (temporary)
def admin_dashboard(request):
    return render(request,'library/admin_dashboard.html')

def member_dashboard(request):
    return render(request,'library/member_dashboard.html')

# book list views-->

@login_required
def book_list(request):
    books = Book.objects.all()
    
    #search filter
    search = request.GET.get('search')
    if search:
        books = books.filter(title__icontains=search) | \
                books.filter(author__icontains=search) 
    
    #category filter
    category = request.GET.get('category')
    if category:
        books = books.filter(category=category)

    return render(request,'library/book_list.html', {'books': books})

# add book
@login_required
def book_add(request):
    if request.method == 'POST':
        title = request.POST['title']
        author = request.POST['author']
        category = request.POST['category']
        isbn = request.POST['isbn']
        total_copies = int(request.POST['total_copies'])
        description = request.POST.get('description','')

        #check ISBN already exists
        if Book.objects.filter(isbn=isbn).exists():
            messages.error(request,'Book with this ISBN already exists!')
            return redirect('book_add')
        
        Book.objects.create(
            title=title,
            author=author,
            category=category,
            isbn=isbn,
            total_copies=total_copies,
            description=description
        )
        messages.success(request,'Book added successfully!')
        return redirect('book_list')
    return render(request,'library/book_add.html')

#book details
@login_required
def book_detail(request, pk):
    book = Book.objects.get(id=pk)
    return render(request,'library/book_detail.html', {'book': book})

#book edit
@login_required
def book_edit(request, pk):
    book = Book.objects.get(id=pk)

    if request.method == 'POST':
        book.title = request.POST['title']
        book.author = request.POST['author']
        book.category = request.POST['category']
        book.isbn = request.POST['isbn']
        book.total_copies = int(request.POST['total_copies'])
        book.description = request.POST['description','']
        book.save()
        messages.success(request,'Book updated successfully!')
        return redirect('book_list')
    
    return render(request,'library/book_add.html', {'book': book, 'edit_mode': True})

#book delete
@login_required
def book_delete(request, pk):
    book = Book.objects.get(id=pk)
    book.delete()
    messages.success(request,'Book deleted successfully!')
    return redirect('book_list')



# ── Issue Book ────────────────────────────────────
@login_required
def issue_book(request):
    if request.method == 'POST':
        member_id = request.POST['member_id']
        isbn      = request.POST['isbn']

        # Check member exists
        try:
            member = Member.objects.get(member_id=member_id)
        except Member.DoesNotExist:
            messages.error(request, 'Member ID not found!')
            return redirect('issue_book')

        # Check book exists
        try:
            book = Book.objects.get(isbn=isbn)
        except Book.DoesNotExist:
            messages.error(request, 'Book ISBN not found!')
            return redirect('issue_book')

        # Check book available
        if not book.is_available():
            messages.error(request, f'"{book.title}" is not available!')
            return redirect('issue_book')

        # Check member already has this book
        already_issued = IssuedBook.objects.filter(
            member=member,
            book=book,
            returned=False
        ).exists()

        if already_issued:
            messages.error(request, 'This member already has this book!')
            return redirect('issue_book')

        # Issue the book
        due_date = date.today() + timedelta(days=14)
        IssuedBook.objects.create(
            member=member,
            book=book,
            due_date=due_date
        )

        # Reduce available copies
        book.available_copies -= 1
        book.save()

        #Auto send sms on book issue
        send_issue_sms(member, book, due_date)

        messages.success(
            request,
            f'"{book.title}" issued to {member.user.get_full_name()}! '
            f'Due date: {due_date}'
        )
        return redirect('issued_list')

    return render(request, 'library/issue_book.html')


# ── Return Book ───────────────────────────────────
@login_required
def return_book(request):
    if request.method == 'POST':
        member_id = request.POST['member_id']
        isbn      = request.POST['isbn']
        condition = request.POST['condition']

        # Check member exists
        try:
            member = Member.objects.get(member_id=member_id)
        except Member.DoesNotExist:
            messages.error(request, 'Member ID not found!')
            return redirect('return_book')

        # Check book exists
        try:
            book = Book.objects.get(isbn=isbn)
        except Book.DoesNotExist:
            messages.error(request, 'Book ISBN not found!')
            return redirect('return_book')

        # Find issued record
        try:
            issued = IssuedBook.objects.get(
                member=member,
                book=book,
                returned=False
            )
        except IssuedBook.DoesNotExist:
            messages.error(request, 'No active issue record found!')
            return redirect('return_book')

        # Mark as returned
        issued.returned = True
        issued.save()

        # Create return record
        ReturnedBook.objects.create(
            issued_book=issued,
            condition=condition
        )

        # Increase available copies
        book.available_copies += 1
        book.save()

        # Calculate fine if overdue
        if issued.is_overdue():
            fine_amount = issued.days_overdue() * 2
            Fine.objects.create(
                issued_book=issued,
                member=member,
                amount=fine_amount
            )
            messages.warning(
                request,
                f'Book returned! Fine of ₹{fine_amount} has been generated!'
            )
        else:
            messages.success(request, 'Book returned successfully! No fine.')

        return redirect('issued_list')

    return render(request, 'library/return_book.html')


# ── Issued Books List ─────────────────────────────
@login_required
def issued_list(request):
    if request.user.is_staff:
        issued_books = IssuedBook.objects.all().order_by('-issue_date')
    else:
        member = Member.objects.get(user=request.user)
        issued_books = IssuedBook.objects.filter(
            member=member
        ).order_by('-issue_date')

    return render(request, 'library/issued_list.html', {
        'issued_books': issued_books
    })

# ── Admin Dashboard ───────────────────────────────
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('member_dashboard')

    total_books   = Book.objects.count()
    total_members = Member.objects.count()
    total_issued  = IssuedBook.objects.filter(returned=False).count()
    recent_issued = IssuedBook.objects.order_by('-issue_date')[:5]

    # Count overdue
    total_overdue = sum(
        1 for issue in IssuedBook.objects.filter(returned=False)
        if issue.is_overdue()
    )

    return render(request, 'library/admin_dashboard.html', {
        'total_books':   total_books,
        'total_members': total_members,
        'total_issued':  total_issued,
        'total_overdue': total_overdue,
        'recent_issued': recent_issued,
    })


# ── Member Dashboard ──────────────────────────────
@login_required
def member_dashboard(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')

    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        messages.error(request, 'Member profile not found!')
        return redirect('login')

    my_books      = IssuedBook.objects.filter(member=member, returned=False)
    total_issued  = my_books.count()
    total_overdue = sum(1 for b in my_books if b.is_overdue())
    my_fines      = Fine.objects.filter(member=member, paid=False)
    total_fine    = sum(f.amount for f in my_fines)

    return render(request, 'library/member_dashboard.html', {
        'member':        member,
        'my_books':      my_books,
        'total_issued':  total_issued,
        'total_overdue': total_overdue,
        'total_fine':    total_fine,
    })


# ── Fine List ─────────────────────────────────────
@login_required
def fine_list(request):
    if request.user.is_staff:
        fines = Fine.objects.all().order_by('-id')
    else:
        member = Member.objects.get(user=request.user)
        fines  = Fine.objects.filter(member=member).order_by('-id')

    total_pending = sum(f.amount for f in fines if not f.paid)

    return render(request, 'library/fine_list.html', {
        'fines':         fines,
        'total_pending': total_pending,
    })


# ── Mark Fine Paid ────────────────────────────────
@login_required
def mark_fine_paid(request, pk):
    fine      = Fine.objects.get(id=pk)
    fine.paid = True
    fine.save()
    messages.success(request, f'Fine of ₹{fine.amount} marked as paid!')
    return redirect('fine_list')

# generate book barcode
@login_required
def generate_barcode(request, pk):
    if not request.user.is_staff:
        messages.error(request, 'admin access only!')
        return redirect('book_list')
    
    book = Book.objects.get(id=pk)
    success = generate_book_barcode(book)

    if success:
        messages.success(request, f'Barcode generated for "{book.title}"!')
    else:
        messages.error(request, 'Failed to generate barcode!')
    
    return redirect('book_barcode', pk=pk)

#view book barcode
@login_required
def book_barcode(request, pk):
    book = Book.objects.get(id=pk)
    return render(request, 'library/barcode.html', {'book': book})

# send sms
@login_required
def send_sms_view(request):
    if not request.user.is_staff:
        messages.error(request, 'admin access only!')
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        member_id = request.POST['member_id']
        sms_type   = request.POST['sms_type']
        custom_message = request.POST.get('custom_message','')

        #get member
        try:
            member = Member.objects.get(member_id=member_id)
        except Member.DoesNotExist:
            messages.error(request, 'Member ID not found!')
            return redirect('sms_send')
        
        # get active issued book
        issued = IssuedBook.objects.filter(
            member=member,
            returned=False
        ).first()

        #build message
        if custom_message:
            sms_message = custom_message
        else:
            sms_message = get_sms_message(
                sms_type=sms_type,
                member_name=member.user.get_full_name(),
                book_title=issued.book.title if issued else 'N/A',
                due_date=issued.due_date if issued else 'N/A',
                fine=Fine.objects.filter(
                    member=member,
                    paid=False
                ).first()
            )
        
        #send sms
        success = send_sms(member.phone, sms_message)

        if success:
            messages.success(
                request,
                f'SMS sent to {member.user.get_full_name()} successfully!'
            )
        else:
            messages.error(
                request,
                f'SMS failed! Check your API key in utils.py'
            )

        return redirect('sms_send')
    return render(request, 'library/sms_send.html')

# Auto SMS on Book Issue
def send_issue_sms(member, book, due_date):
    sms_message = get_sms_message(
        sms_type = 'issued',
        member_name = member.user.get_full_name(),
        book_title = book.title,
        due_date = due_date
    )
    send_sms(member.phone, sms_message)

# search book
@login_required 
def search_books(request):
    books = Book.objects.all()
    query = ''

    search = request.GET.get('search', '')
    isbn   = request.GET.get('isbn', '')
    category = request.GET.get('category', '')

    if search:
        query = search
        books = books.filter(title__icontains=search) | \
                books.filter(author__icontains=search)
        
    if isbn:
        query = isbn
        books = books.filter(isbn__icontains=isbn)
    
    if category:
        books = books.filter(category=category)
    
    return render(request, 'library/search_results.html', {
        'books': books,
        'query': query,
        })
    
# reserve book
@login_required
def reserve_book(request, pk):
    book = Book.objects.get(id=pk)

    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        messages.error(request, 'Member profile not found!')
        return redirect('search_books')

    # ── Check 1 — Book already issued to this member ──
    already_issued = IssuedBook.objects.filter(
        member=member,
        book=book,
        returned=False
    ).exists()

    if already_issued:
        messages.warning(
            request,
            f'This book is already issued to you!'
        )
        return redirect('search_books')

    # ── Check 2 — Already reserved by this member ──
    already_reserved = Reservation.objects.filter(
        member=member,
        book=book,
        active=True
    ).exists()

    if already_reserved:
        messages.warning(
            request,
            f'You already reserved "{book.title}"!'
        )
        return redirect('my_reservations')

    # ── Check 3 — Book is available no need to reserve ──
    if book.is_available():
        messages.info(
            request,
            f'"{book.title}" is already available! '
            f'No need to reserve. You can issue it directly.'
        )
        return redirect('search_books')

    # ── All checks passed — Create reservation ──
    Reservation.objects.create(
        member=member,
        book=book
    )

    messages.success(
        request,
        f'"{book.title}" reserved successfully! '
        f'You will be notified when available.'
    )
    return redirect('my_reservations')

# cancel reservation
@login_required
def cancel_reservation(request, pk):
    reservation = Reservation.objects.get(id=pk)
    reservation.active = False
    reservation.save()
    messages.success(request, 'reservation cancelled successfully!')
    return redirect('my_reservations')

#all reservation admin view
@login_required
def reservation_list(request):
    if not request.user.is_staff:
        return redirect('my_reservations')
    
    reservations = Reservation.objects.all().order_by('-reservation_date')
    return render(request, 'library/reservation_list.html', {
        'reservations': reservations
    })

# my reservations - member view
@login_required
def my_reservations(request):
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        messages.error(request, 'Member profile not found!')
        return redirect('login')
    
    reservations = Reservation.objects.filter(
        member=member,
    ).order_by('-reservation_date')

    return render(request, 'library/my_reservations.html', {
        'reservations': reservations
    })

@login_required
def member_list(request):
    if not request.user.is_staff:
        messages.redirect('member_dashboard')
    members = Member.objects.all().order_by('member_id')
    return render(request, 'library/member_list.html', {
        'members': members
    })