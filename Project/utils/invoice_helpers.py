"""
Helper functions to reduce cognitive complexity in main.py
"""
import pandas as pd
import streamlit as st
from typing import Tuple, List, Dict
from utils.payment_engine import trigger_payment
from genAI.justification import generate_payment_justification
from genAI.risk_recommender import generate_risk_recommendation
from utils.email_sender import send_invoice_escalation_email, generate_escalation_email_content

# Constants from main.py
DATE_FORMAT = '%b %d %Y'
FIELD_QUANTITY_MISMATCH = 'Quantity Mismatch'
FIELD_RATE_MISMATCH = 'Rate Mismatch'
FIELD_AMOUNT_MISMATCH = 'Amount Mismatch'
FIELD_TOTAL_MISMATCH = 'Total Mismatch'
FIELD_OVERBILLING = 'Overbilling'

def create_payment_log_entry(row: pd.Series, transaction_type: str = 'auto') -> Dict:
    """Create a payment log entry for a given invoice row."""
    if transaction_type == 'previous':
        return {
            'order_id': row['order_id'],
            'customer_name': row['customer_name'],
            'due_date': row['due_date'],
            'amount': row['total'],
            'transaction_id': 'PREVIOUSLY_PAID',   
            'status': 'SUCCESS',
            'timestamp': pd.Timestamp.now().isoformat(),
            'message': 'Auto-paid earlier',
            'justification': 'Previously paid for past due invoice',
            'payment_mode': 'PreviouslyPaid'
        }
    else:
        payment_response = trigger_payment(row['order_id'], row['customer_name'], row['total'], row['due_date'])
        invoice_row = {
            'order_id': row['order_id'],
            'customer_name': row['customer_name'],
            'amount': row['total'],
            'due_date': row['due_date']
        }
        justification = generate_payment_justification(invoice_row)
        return {
            'order_id': row['order_id'],
            'customer_name': row['customer_name'],
            'due_date': row['due_date'],
            'amount': row['total'],
            'transaction_id': payment_response.get('transaction_id', ''),   
            'status': payment_response.get('status', ''),
            'timestamp': payment_response.get('timestamp', ''),
            'message': payment_response.get('message', ''),
            'justification': justification,
            'payment_mode': 'Auto'
        }

def process_past_due_invoices(validation_report_df: pd.DataFrame, existing_log_df: pd.DataFrame) -> List[Dict]:
    """Process past due invoices and mark them as previously paid."""
    payment_log_entries = []
    past_due_invoices = validation_report_df[
        (pd.to_datetime(validation_report_df['due_date'], format=DATE_FORMAT).dt.strftime('%Y-%m-%d') < pd.Timestamp.now().strftime('%Y-%m-%d')) & 
        (validation_report_df['validation_status'] == 'VALID')
    ]
    
    for _, row in past_due_invoices.iterrows():
        already_paid = not existing_log_df[
            (existing_log_df['order_id'] == row['order_id']) & 
            (existing_log_df['customer_name'] == row['customer_name'])
        ].empty
        
        if not already_paid:
            payment_log_entries.append(create_payment_log_entry(row, 'previous'))
    
    return payment_log_entries

def process_todays_invoices(validation_report_df: pd.DataFrame, existing_log_df: pd.DataFrame) -> List[Dict]:
    """Process today's invoices and trigger payments for valid ones."""
    payment_log_entries = []
    today_invoices = validation_report_df[
        pd.to_datetime(validation_report_df['due_date'], format=DATE_FORMAT).dt.strftime('%Y-%m-%d') == pd.Timestamp.now().strftime('%Y-%m-%d')
    ]
    
    for _, row in today_invoices.iterrows():
        if row['validation_status'] == 'VALID':
            already_paid = not existing_log_df[
                (existing_log_df['order_id'] == row['order_id']) & 
                (existing_log_df['customer_name'] == row['customer_name'])
            ].empty
            
            if not already_paid:
                payment_log_entries.append(create_payment_log_entry(row, 'auto'))
    
    return payment_log_entries

def calculate_invoice_metrics(validation_report_df: pd.DataFrame, existing_payment_log_df: pd.DataFrame) -> Tuple[int, int, int, int, int]:
    """Calculate invoice metrics for display."""
    total_invoices = len(validation_report_df)
    valid_invoices = len(validation_report_df[validation_report_df['validation_status'] == 'VALID'])
    flagged_invoices = total_invoices - valid_invoices
    
    today_date = pd.Timestamp.now().strftime('%Y-%m-%d')
    paid_today_invoices = len(existing_payment_log_df[
        (pd.to_datetime(existing_payment_log_df['due_date'], format=DATE_FORMAT).dt.strftime('%Y-%m-%d') == today_date) & 
        (existing_payment_log_df['status'] == 'SUCCESS')
    ])
    
    over_due_unpaid_invoices = len(validation_report_df[
        (pd.to_datetime(validation_report_df['due_date'], format=DATE_FORMAT).dt.strftime('%Y-%m-%d') < today_date) & 
        (validation_report_df['validation_status'] == 'INVALID')
    ])
    
    return total_invoices, valid_invoices, flagged_invoices, paid_today_invoices, over_due_unpaid_invoices

def display_invoice_metrics(total_invoices: int, valid_invoices: int, flagged_invoices: int, paid_today_invoices: int, over_due_unpaid_invoices: int):
    """Display invoice metrics in a grid layout."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Invoices", total_invoices, help="All processed invoices")
    with col2:
        st.metric("Flagged Invoices", flagged_invoices, help="Invoices requiring attention")
    with col3:            
        st.metric("Overdue Invoices", over_due_unpaid_invoices, help="Past due invoices")
    
    col4, col5, col6 = st.columns(3)
    with col4:            
        st.metric("Clean Invoices", valid_invoices, help="Successfully validated invoices")
    with col5:
        st.metric("Paid Today", paid_today_invoices, help="Payments processed today")
    with col6:
        st.metric(" ", " ", help=" ")

def build_field_comparison(row: pd.Series) -> List[Dict]:
    """Build field comparison list for escalation emails."""
    field_comparison = []
    mismatched_fields = row['validation_result'].split(',')
    
    for field in mismatched_fields:
        field = field.strip()
        if field == FIELD_QUANTITY_MISMATCH:
            field_comparison.append({
                'field': 'Quantity',
                'invoice_value': str(int(row['quantity_inv'])),
                'po_value': str(int(row['quantity_po']))
            })
        elif field == FIELD_RATE_MISMATCH:
            field_comparison.append({
                'field': 'Rate',
                'invoice_value': f"${row['rate_inv']}",
                'po_value': f"${row['rate_po']}"
            })
        elif field in [FIELD_AMOUNT_MISMATCH, FIELD_TOTAL_MISMATCH, FIELD_OVERBILLING]:
            field_comparison.append({
                'field': 'Total Amount',
                'invoice_value': f"${row['amount']}",
                'po_value': f"${row['expected_amount']}"
            })
    
    return field_comparison

def handle_invalid_invoice(row: pd.Series):
    """Handle invalid invoices with risk recommendation and escalation."""
    recommendation = generate_risk_recommendation(row.to_dict())
    st.error(f"🚨 Recommendation: {recommendation['recommendation']}")
    st.caption(f"Reason: {recommendation['reason']}") 
    
    if recommendation['recommendation'].strip().lower() == 'escalate':
        field_comparison = build_field_comparison(row)
        
        subject, body = generate_escalation_email_content(
            order_id=row['order_id'],
            customer=row['customer_name'],
            amount=row['total'],
            due_date=row['due_date'],
            ai_recommendation=recommendation['recommendation'],
            reason=recommendation['reason'],
            field_comparison=field_comparison
        )
        
        send_invoice_escalation_email(
            subject=subject,
            body=body,
            recipient_email=['abindash@virtusa.com','adash@wiley.com']
        )

def handle_valid_invoice(row: pd.Series, existing_payment_log_df: pd.DataFrame):
    """Handle valid invoices with payment status display."""
    already_paid = existing_payment_log_df[
        (existing_payment_log_df['order_id'] == row['order_id']) & 
        (existing_payment_log_df['customer_name'] == row['customer_name'])
    ]
    
    if not already_paid.empty:
        justification = already_paid.iloc[0]['justification']
        if already_paid.iloc[0]['status'] == 'SUCCESS':   
            st.success(f"✅ {justification}")
        else:
            st.warning(f"⚠️ Payment attempted but did not succeed. Payment Status: {already_paid.iloc[0]['status']}, Payment Message:{already_paid.iloc[0]['message']}")
            st.warning(f"{justification}")
    else:
        justification = "Payment not yet processed."
        st.warning(f"⏳ {justification}")

def build_display_dataframes(existing_payment_log_df: pd.DataFrame, validation_report_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Build dataframes for display purposes."""
    # Build payment log display dataframe
    displayed_payment_log_df = pd.DataFrame(columns=['order_id', 'customer_name', 'amount', 'due_date', 'transaction_id', 'status', 'timestamp', 'days_until_due', 'message', 'payment_mode'])
    
    for _, row in existing_payment_log_df.iterrows():
        displayed_payment_log_df = pd.concat([displayed_payment_log_df, pd.DataFrame([{
            'order_id': row['order_id'],
            'customer_name': row['customer_name'],
            'amount': row['amount'],
            'due_date': row['due_date'],
            'transaction_id': row['transaction_id'],
            'status': row['status'],
            'timestamp': row['timestamp'],
            'days_until_due': (pd.to_datetime(row['due_date'], format=DATE_FORMAT) - pd.Timestamp.now()).days,
            'message': row['message'],
            'payment_mode': row['payment_mode']
        }])], ignore_index=True)
    
    displayed_payment_log_df = displayed_payment_log_df.sort_values(by=['timestamp','due_date'], ascending=False)
    
    # Build overdue unpaid display dataframe
    displayed_overdue_unpaid_df = pd.DataFrame(columns=['order_id', 'customer_name', 'amount', 'due_date', 'status', 'validation_result', 'days_until_due'])
    
    for _, row in validation_report_df.iterrows():
        due_date_formatted = pd.to_datetime(row['due_date'], format=DATE_FORMAT).strftime('%Y-%m-%d')
        days_until_due = (pd.to_datetime(due_date_formatted, format='%Y-%m-%d') - pd.Timestamp.now()).days
        if days_until_due < 0 and row['validation_status'] == 'INVALID':
            displayed_overdue_unpaid_df = pd.concat([displayed_overdue_unpaid_df, pd.DataFrame([{
                'order_id': row['order_id'],
                'customer_name': row['customer_name'],
                'amount': row['total'],
                'due_date': row['due_date'],
                'status': 'Flagged',
                'validation_result': row['validation_result'],
                'days_until_due': days_until_due
            }])], ignore_index=True)
    
    displayed_overdue_unpaid_df = displayed_overdue_unpaid_df.sort_values(by='due_date', ascending=False)
    
    return displayed_payment_log_df, displayed_overdue_unpaid_df