import barcode
from barcode.writer import ImageWriter
from django.core.files import File
from django.core.files.base import ContentFile
from django.conf import settings
import os
import io
import requests


# ── Generate Barcode ──────────────────────────────
def generate_book_barcode(book):
    try:
        # Use memory instead of temp file
        CODE128 = barcode.get_barcode_class('code128')

        # Write to memory buffer
        buffer = io.BytesIO()
        code   = CODE128(str(book.isbn), writer=ImageWriter())
        code.write(buffer)

        # Save to book
        filename = f'barcode_{book.isbn}.png'
        book.barcode_image.save(
            filename,
            ContentFile(buffer.getvalue()),
            save=True
        )
        buffer.close()
        print(f'Barcode generated successfully for {book.isbn}')
        return True

    except Exception as e:
        print(f'Barcode Error: {e}')
        return False


# ── Send SMS via Fast2SMS ─────────────────────────
def send_sms(phone, message):
    try:
        from twilio.rest import Client

        account_sid = 'YOUR_TWILIO_ACCOUNT_SID' 
        auth_token  = 'YOUR_TWILIO_AUTH_TOKEN'
        client      = Client(account_sid, auth_token)

        msg = client.messages.create(
            body=message,
            from_='YOUR_TWILIO_PHONE_NUMBER',  # twilio number
            to=f'+91{phone}'
        )
        print(f'SMS Sent! SID: {msg.sid}')
        return True

    except Exception as e:
        print(f'SMS Error: {e}')
        return False


# ── SMS Message Templates ─────────────────────────
def get_sms_message(sms_type, member_name, book_title=None, due_date=None, fine=None):
    messages = {
        'issued': (
            f'Dear {member_name}, '
            f'"{book_title}" issued. '
            f'Return by {due_date}. '
            f'Library Management System.'
        ),
        'due': (
            f'Dear {member_name}, '
            f'"{book_title}" due on {due_date}. '
            f'Please return on time. '
            f'Library Management System.'
        ),
        'overdue': (
            f'Dear {member_name}, '
            f'"{book_title}" is overdue! '
            f'Return immediately. '
            f'Library Management System.'
        ),
        'fine': (
            f'Dear {member_name}, '
            f'Fine of Rs.{fine} generated. '
            f'Please pay soon. '
            f'Library Management System.'
        ),
    }
    return messages.get(sms_type, 'Library notification.')