"""
Escalation Email System for Invoice Validation

This module provides secure email functionality for escalating problematic invoices to finance controllers.
The system sends formal escalation emails that include:
•	Key invoice details (Order ID, Customer, Amount, Due Date)
•	AI-generated recommendation and reason for escalation
•	A clear field-by-field comparison table showing mismatches between invoice and purchase order
•	This empowers finance teams to take timely action based on AI decisions

SECURITY FEATURES:
- Environment variable-based configuration (no hardcoded credentials)
- Standard Python smtplib with SSL/TLS encryption
- Supports both STARTTLS (port 587) and implicit SSL (port 465)
- Minimal error handling for security
- Input validation for email addresses
- Support for multiple SMTP providers (Gmail, Outlook, Yahoo, custom)

SETUP REQUIREMENTS:
1. Copy .env.template to .env
2. Set SMTP_USERNAME and SMTP_PASSWORD in .env file
3. For Gmail: Use App Password, not regular password
4. Optionally configure SMTP_SERVER and SMTP_PORT
   - Port 587 (default): STARTTLS (recommended for Gmail)
   - Port 465: Implicit SSL
5. Optionally set DEFAULT_SENDER_EMAIL

USAGE EXAMPLES:
    # Generate escalation email content with table format
    subject, body = generate_escalation_email_content(
        order_id="ES-2025-001", 
        customer="Acme Corp", 
        amount=1500.00,
        due_date="Nov 15 2025",
        ai_recommendation="Escalate",
        reason="Quantity Mismatch",
        field_comparison=[
            {'field': 'Quantity', 'invoice_value': '100', 'po_value': '50'},
            {'field': 'Rate', 'invoice_value': '$15.00', 'po_value': '$15.00'},
            {'field': 'Total Amount', 'invoice_value': '$1,500.00', 'po_value': '$750.00'}
        ]
    )
    
    # Also supports legacy string format for backward compatibility
    subject, body = generate_escalation_email_content(
        order_id="ES-2025-001", 
        customer="Acme Corp", 
        amount=1500.00,
        due_date="Nov 15 2025",
        ai_recommendation="Escalate",
        reason="Quantity Mismatch",
        field_comparison="Invoice: 100 items, PO: 50 items"
    )
    
    # Then send the escalation email
    result = send_invoice_escalation_email(
        subject=subject,
        body=body,
        recipient_email="finance@company.com"  # Or ["finance@company.com", "manager@company.com"]
    )
    
    # Check configuration status
    status = configure_email_settings()
    print(f"Email configured: {status['configured']}")

Sample Email Contents:
Subject: Escalation Alert: Invoice ES-2025-BE11335139-41340 Requires Review
Body: (HTML formatted with table)
Order ID: ES-2025-BE11335139-41340
Customer: Bill Eplett
Amount: $9466.50
Due Date: Aug 06 2025
AI Recommendation: Escalate
Reason: Quantity Mismatch, Overbilling
Field Comparison Table:
┌──────────────┬────────────────┬──────────┐
│ Field        │ Invoice Value  │ PO Value │
├──────────────┼────────────────┼──────────┤
│ Quantity     │ 150            │ 100      │
│ Rate         │ $63.11         │ $63.11   │
│ Total Amount │ $9,466.50      │ $6,311.00│
└──────────────┴────────────────┴──────────┘
Please review this invoice and take appropriate action.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def generate_escalation_email_content(order_id, customer, amount, due_date, ai_recommendation, reason, field_comparison):
    """
    Generate escalation email content with field comparison table.
    
    Args:
        field_comparison (list): List of dicts with keys: 'field', 'invoice_value', 'po_value'
                                Example: [
                                    {'field': 'Quantity', 'invoice_value': '100', 'po_value': '50'},
                                    {'field': 'Rate', 'invoice_value': '$10.00', 'po_value': '$9.50'}
                                ]
    """
    subject = f"Escalation Alert: Invoice {order_id} Requires Review"
    
    # Generate table HTML if field_comparison is a list
    if isinstance(field_comparison, list) and field_comparison:
        table_rows = ""
        for item in field_comparison:
            table_rows += f"""
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['field']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['invoice_value']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['po_value']}</td>
            </tr>"""
        
        field_comparison_html = f"""
        <table style="border-collapse: collapse; width: 100%; margin-top: 10px;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Field</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Invoice Value</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">PO Value</th>
                </tr>
            </thead>
            <tbody>{table_rows}
            </tbody>
        </table>"""
    else:
        # Fallback for string input (backward compatibility)
        field_comparison_html = f"<pre>{field_comparison}</pre>"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #d9534f;">Invoice Escalation Alert</h2>
        <p><strong>Order ID:</strong> {order_id}</p>
        <p><strong>Customer:</strong> {customer}</p>
        <p><strong>Amount:</strong> ${amount}</p>
        <p><strong>Due Date:</strong> {due_date}</p>
        <p><strong>AI Recommendation:</strong> <span style="color: #d9534f;">{ai_recommendation}</span></p>
        <p><strong>Reason:</strong> {reason}</p>
        <h3>Field Comparison:</h3>
        {field_comparison_html}
        <p style="margin-top: 20px;"><em>Please review this invoice and take appropriate action.</em></p>
    </body>
    </html>
    """
    return subject, body

def send_invoice_escalation_email(subject, body, recipient_email, sender_email=None):
    """
    Send escalation email with pre-generated subject and body content.
    
    Args:
        subject (str): Email subject line
        body (str): Email body content
        recipient_email (str or list): Finance controller email(s) - single email or list of emails
        sender_email (str, optional): Sender email (defaults to env variable)
    
    Returns:
        dict: Result containing success status and message
    """
    # Use provided sender email or get from environment
    if not sender_email:
        sender_email = os.getenv('DEFAULT_SENDER_EMAIL', 'invoiceguard@company.com')
    
    # Send the escalation email
    send_email(sender_email, recipient_email, subject, body)
    
    

def configure_email_settings():
    """
    Helper function to check and display email configuration status.
    
    Returns:
        dict: Configuration status and recommendations
    """
    config_status = {
        'smtp_server': os.getenv('SMTP_SERVER', 'Not set (using default: smtp.gmail.com)'),
        'smtp_port': os.getenv('SMTP_PORT', 'Not set (using default: 587)'),
        'smtp_username': 'Set' if os.getenv('SMTP_USERNAME') else 'Not set - REQUIRED',
        'smtp_password': 'Set' if os.getenv('SMTP_PASSWORD') else 'Not set - REQUIRED',
        'default_sender': os.getenv('DEFAULT_SENDER_EMAIL', 'Not set (using default: invoiceguard@company.com)')
    }
    
    is_configured = bool(os.getenv('SMTP_USERNAME') and os.getenv('SMTP_PASSWORD'))
    
    recommendations = []
    if not os.getenv('SMTP_USERNAME'):
        recommendations.append("Set SMTP_USERNAME environment variable")
    if not os.getenv('SMTP_PASSWORD'):
        recommendations.append("Set SMTP_PASSWORD environment variable (use app-specific password for Gmail)")
    if not os.getenv('DEFAULT_SENDER_EMAIL'):
        recommendations.append("Optionally set DEFAULT_SENDER_EMAIL environment variable")
    
    return {
        'configured': is_configured,
        'settings': config_status,
        'recommendations': recommendations
    }
def send_email(from_email, to_email, subject, body):
    """Send escalation email using STARTTLS (587) or SSL (465) with minimal logic.

    Args:
        from_email (str): Sender email address
        to_email (str or list): Recipient email address(es) - single email or list of emails
        subject (str): Email subject line
        body (str): Email body content

    Expected environment variables:
    - SMTP_SERVER (default: smtp.gmail.com)
    - SMTP_PORT   (default: 587 for STARTTLS, or 465 for SSL)
    - SMTP_USERNAME (required)
    - SMTP_PASSWORD (required)
    """
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))  # STARTTLS default (Gmail standard)
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')

    if not smtp_username or not smtp_password:
        return {'success': False, 'message': 'Missing SMTP credentials'}
    
    # Convert to_email to list if it's a string
    to_email_list = [to_email] if isinstance(to_email, str) else to_email
    
    # Validate all email addresses
    if '@' not in (from_email or ''):
        return {'success': False, 'message': 'Invalid sender email address'}
    for email in to_email_list:
        if '@' not in (email or ''):
            return {'success': False, 'message': f'Invalid recipient email address: {email}'}

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(to_email_list)  # Join multiple emails with comma
    
    # Add both plain text and HTML versions for better compatibility
    # Check if body contains HTML tags
    if '<html>' in body.lower() or '<table>' in body.lower():
        # Create plain text version by stripping HTML (simple version)
        plain_text = body.replace('<html>', '').replace('</html>', '')
        plain_text = plain_text.replace('<body', '').replace('</body>', '')
        plain_text = plain_text.replace('<h2>', '\n').replace('</h2>', '\n')
        plain_text = plain_text.replace('<h3>', '\n').replace('</h3>', '\n')
        plain_text = plain_text.replace('<p>', '').replace('</p>', '\n')
        plain_text = plain_text.replace('<strong>', '').replace('</strong>', '')
        plain_text = plain_text.replace('<em>', '').replace('</em>', '')
        plain_text = plain_text.replace('<span', '').replace('</span>', '')
        # Remove style attributes
        import re
        plain_text = re.sub(r'style="[^"]*"', '', plain_text)
        plain_text = plain_text.replace('>','')
        
        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(body, 'html', 'utf-8'))
    else:
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
   
    # Use STARTTLS (587) or implicit SSL (465) based on port
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, to_email_list, msg.as_string())
    else:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, to_email_list, msg.as_string())
    
    