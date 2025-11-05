'''
This is the core controller script of the project, built using Streamlit. Expected to integrate all modular components (PDF extraction, validation, payment logic, GenAI reasoning, and visualization) and display the end-to-end functionality of the Invoice Automation System.
'''
import streamlit as st
from utils.pdf_extractor import extract_raw_text
from genAI.parser import parse_invoice_with_genai
from utils.validation import validate_invoices
from genAI.region_summarizer import summarize_regions
from utils.invoice_helpers import (
    process_past_due_invoices, process_todays_invoices, 
    calculate_invoice_metrics, display_invoice_metrics,
    handle_valid_invoice, handle_invalid_invoice,
    build_display_dataframes
)
import pandas as pd
import os
import plotly.express as px

# Constants
INVOICES_CSV_PATH = "output/invoices.csv"
PAYMENT_LOG_CSV_PATH = "output/payment_log.csv"
VALIDATION_REPORT_CSV_PATH = "output/validation_report.csv"
PURCHASE_ORDERS_CSV_PATH = "data/purchase_orders.csv"
PDF_FOLDER_PATH = "data/Invoice/"
DATE_FORMAT = '%b %d %Y'

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    print(f"⚠️ Error loading .env file: {e}")

def analyze_invoices(pdf_folder: str):
    """Analyze invoices in the given folder and save to output/invoices.csv"""
    parsed_invoices = []
    for pdf_file in os.listdir(pdf_folder):
        if pdf_file.endswith(".pdf"):
            file_path = os.path.join(pdf_folder, pdf_file)
            raw_text = extract_raw_text(file_path)
            parsed_invoice = parse_invoice_with_genai(raw_text)
            if parsed_invoice is None:
                break
            parsed_invoice['file_name'] = pdf_file
            
            # Flatten item_details (1 row per item)
            for item in parsed_invoice.get('item_details', []):
                invoice_copy = parsed_invoice.copy()
                invoice_copy['item_name'] = item.get('item_name', '')
                invoice_copy['quantity'] = item.get('quantity', 0)
                invoice_copy['rate'] = item.get('rate', 0.0)
                invoice_copy['amount'] = item.get('amount', 0.0)
                invoice_copy.pop('item_details', None)
                parsed_invoices.append(invoice_copy)

    invoices_df = pd.DataFrame(parsed_invoices)
    invoices_df.to_csv(INVOICES_CSV_PATH, index=False)

def load_existing_payment_log() -> pd.DataFrame:
    """Load existing payment log if exists"""
    if os.path.exists(PAYMENT_LOG_CSV_PATH):
        return pd.read_csv(PAYMENT_LOG_CSV_PATH)
    else:
        return pd.DataFrame(columns=['order_id', 'customer_name', 'due_date', 'amount', 'transaction_id', 'status', 'timestamp', 'message','justification','payment_mode'])

def load_existing_validation_report() -> pd.DataFrame:
    """Load existing validation report if exists"""
    if os.path.exists(VALIDATION_REPORT_CSV_PATH):
        return pd.read_csv(VALIDATION_REPORT_CSV_PATH)
    else:
        return pd.DataFrame(columns=['order_id', 'customer_name', 'due_date', 'amount', 'transaction_id', 'status', 'timestamp', 'message','justification','payment_mode'])

def process_payments_and_past_due(validation_report_df: pd.DataFrame):
    """Process today's payments and past due invoices"""
    existing_log_df = load_existing_payment_log()   
    
    # Process invoices
    past_due_entries = process_past_due_invoices(validation_report_df, existing_log_df)
    todays_entries = process_todays_invoices(validation_report_df, existing_log_df)
    
    # Combine and save entries
    all_entries = past_due_entries + todays_entries
    if all_entries:
        payment_log_df = pd.DataFrame(all_entries)
        if existing_log_df.empty:
            existing_log_df = payment_log_df.copy()
        else:
            existing_log_df = pd.concat([existing_log_df, payment_log_df], ignore_index=True)   
    
    existing_log_df.to_csv(PAYMENT_LOG_CSV_PATH, index=False)

def render_tab1():
    """Render Tab 1: Invoice Table"""
    status_placeholder = st.empty()
    status_placeholder.info("🔄 Processing invoices, validating, and initiating payments...")
    
    # Load or extract invoice data
    if not os.path.exists(INVOICES_CSV_PATH):
        analyze_invoices(PDF_FOLDER_PATH)
        
    if not os.path.exists(INVOICES_CSV_PATH):
        st.error(f"⚠️ Invoices CSV file not found in {INVOICES_CSV_PATH}.")
        return
        
    if not os.path.exists(PURCHASE_ORDERS_CSV_PATH):
        st.error("⚠️ purchase_orders.csv file not found in data/ folder.")
        return

    # Process data
    invoices_df = pd.read_csv(INVOICES_CSV_PATH)
    po_df = pd.read_csv(PURCHASE_ORDERS_CSV_PATH)
    validation_report_df = validate_invoices(invoices_df, po_df)
    validation_report_df.to_csv(VALIDATION_REPORT_CSV_PATH, index=False)
    
    process_payments_and_past_due(validation_report_df)
    
    # Display metrics
    existing_payment_log_df = load_existing_payment_log()
    metrics = calculate_invoice_metrics(validation_report_df, existing_payment_log_df)
    display_invoice_metrics(*metrics)
    
    # Display tables
    displayed_payment_log_df, displayed_overdue_unpaid_df = build_display_dataframes(existing_payment_log_df, validation_report_df)
    
    if not displayed_payment_log_df.empty:
        st.subheader("Payment Log")
        st.dataframe(displayed_payment_log_df)
        
    if not displayed_overdue_unpaid_df.empty:
        st.subheader("Overdue and Unpaid Invoices")
        st.warning(f"{len(displayed_overdue_unpaid_df)} overdue invoices not yet paid.")
        st.dataframe(displayed_overdue_unpaid_df)
    
    status_placeholder.empty()

def render_tab2():
    """Render Tab 2: Today's Orders"""
    existing_payment_log_df = load_existing_payment_log()
    validation_report_df = load_existing_validation_report()
    today_invoices = validation_report_df[
        pd.to_datetime(validation_report_df['due_date'], format=DATE_FORMAT).dt.strftime('%Y-%m-%d') == pd.Timestamp.now().strftime('%Y-%m-%d')
    ]
    
    if today_invoices.empty:
        st.info("🎉 No invoices due today!")
        return
    
    for _, row in today_invoices.iterrows():
        st.subheader(f"Order ID: {row['order_id']} | Customer: {row['customer_name']}")
        
        if row['validation_status'] == 'VALID':
            handle_valid_invoice(row, existing_payment_log_df)
        else:
            handle_invalid_invoice(row)

def render_tab3():
    """Render Tab 3: Global Metrics"""
    validation_report_df = load_existing_validation_report()
    
    if validation_report_df.empty:
        st.warning("⚠️ No validation data available. Please process invoices first.")
        return
    
    # Extract region and create summary
    validation_report_df['region'] = validation_report_df['ship_to'].astype(str).str.strip().apply(
        lambda x: x.split(',')[-1].strip() if ',' in x and x else 'Unknown'
    )
    
    region_summary_df = validation_report_df.groupby('region').agg(
        total_sales=('total', 'sum'),
        total_shipping=('shipping_cost', 'sum'),
        num_invoices=('region', 'count')
    ).reset_index()
    
    st.dataframe(region_summary_df, use_container_width=True)
    
    # Charts
    st.subheader("Total Sales by Region")
    region_summary_sorted = region_summary_df.sort_values('total_sales', ascending=False)
    fig_sales = px.bar(region_summary_sorted, x='region', y='total_sales', title='Total Sales by Region')
    fig_sales.update_layout(xaxis_title='Region', yaxis_title='Total Sales')
    st.plotly_chart(fig_sales, use_container_width=True)
    
    st.subheader("Total Shipping Cost by Region")
    region_summary_sorted_shipping = region_summary_df.sort_values('total_shipping', ascending=False)
    fig_shipping = px.bar(region_summary_sorted_shipping, x='region', y='total_shipping', title='Total Shipping Cost by Region')
    fig_shipping.update_layout(xaxis_title='Region', yaxis_title='Total Shipping Cost')
    st.plotly_chart(fig_shipping, use_container_width=True)
    
    # GenAI summary
    st.subheader("GenAI Region Summary")
    region_summary = summarize_regions(region_summary_df)
    for summaryline in region_summary['summary']:
        st.markdown(f"• {summaryline}")
    st.markdown("###### *Insight:*")
    st.write(f"{region_summary['insight']}")

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="InvoiceGuard: Automated Validation, Payment & Regional Insights",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("InvoiceGuard: Automated Validation, Payment & Regional Insights")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Invoice Table", "Today's Orders", "Global Metrics"])
    
    with tab1:
        render_tab1()
    
    with tab2:
        render_tab2()
    
    with tab3:
        render_tab3()

if __name__ == "__main__":
    main()