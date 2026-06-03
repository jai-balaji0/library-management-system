from django.urls import path
from . import views

urlpatterns = [
    path('',views.login_view, name='login'),
    path('register/',views.register_view, name='register'),
    path('logout/',views.logout_view, name='logout'),

    path('admin-dashboard/',views.admin_dashboard, name='admin_dashboard'),
    path('member-dashboard/',views.member_dashboard, name='member_dashboard'),

    path('books/',views.book_list, name='book_list'),
    path('books/add/',views.book_add, name='book_add'),
    path('books/<int:pk>/',views.book_detail, name='book_detail'),
    path('books/<int:pk>/edit/',views.book_edit, name='book_edit'),
    path('books/<int:pk>/delete/',views.book_delete, name='book_delete'),

    path('issue/', views.issue_book, name='issue_book'),
    path('return/', views.return_book, name='return_book'),
    path('issued/', views.issued_list, name='issued_list'),

    path('fines/', views.fine_list, name='fine_list'),
    path('fines/<int:pk>/paid/', views.mark_fine_paid, name='mark_fine_paid'),

    path('books/<int:pk>/barcode/', views.book_barcode, name='book_barcode'),
    path('books/<int:pk>/generate-barcode/', views.generate_barcode, name='generate_barcode'), 
    path('members/', views.member_list, name='member_list'),

    path('sms/', views.send_sms_view, name='sms_send'),

    path('search/', views.search_books, name='search_books'),
    path('books/<int:pk>/reserve/', views.reserve_book, name='reserve_book'),
    path('reservations/', views.reservation_list, name='reservation_list'),
    path('reservations/my/', views.my_reservations, name='my_reservations'),
    path('reservations/<int:pk>/cancel/', views.cancel_reservation, name='cancel_reservation'),
]
