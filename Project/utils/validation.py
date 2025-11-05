import pandas as pd
import ast
def _check_missing_po(row):
    """Check if PO data is missing"""
    return pd.isna(row['quantity_po']) or pd.isna(row['rate_po']) or pd.isna(row['expected_amount'])
def _get_validation_reasons(row):
    """get list of validation reasons"""
    reasons=[]
    # Compare quantity
    if row['quantity_inv'] != row['quantity_po']:
        reasons.append("Quantity Mismatch")
    # Compare rate
    if row['rate_inv'] != row['rate_po']:
        reasons.append("Rate Mismatch")
    # Compare amount
    if row['amount'] > row['expected_amount']:
        reasons.append("Overbilling")
    elif row['amount'] < row['expected_amount']:
        reasons.append("Amount Mismatch")
    return reasons
def validate_invoices(invoices_df: pd.DataFrame, po_df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate extracted invoice data against purchase orders.
    Matching is based on (invoice_number, order_id, customer_name).
    Returns a validation report DataFrame with status and reasons.
    """
    # Ensure invoice_number columns have the same data type
    invoices_df['invoice_number'] = invoices_df['invoice_number'].astype(int)
    po_df['invoice_number'] = po_df['invoice_number'].astype(int)
    #rename invoice_number to avoid merge conflict
    invoices_df.rename(columns={'invoice_number': 'invoice_number_inv'}, inplace=True)
    # Merge invoices with purchase orders on matching keys
    merged_df = pd.merge(
        invoices_df,
        po_df,  
        how='left',
        left_on=['invoice_number_inv', 'order_id', 'customer_name'],
        right_on=['invoice_number', 'order_id', 'customer_name'],
        suffixes=('_inv', '_po'),
        validate='one_to_one'
    )
    # Initialize validation result columns
    merged_df['validation_result'] = '' 
    merged_df['validation_status'] = 'VALID'
    # Iterate through merged DataFrame to validate each invoice
    for index, row in merged_df.iterrows():
        reasons = []
        # Check if PO exists
        if _check_missing_po(row):
            reasons.append("Missing PO")
        else:
            reasons= _get_validation_reasons(row)
        # Set validation result and status
        if reasons:
            merged_df.at[index, 'validation_result'] = ', '.join(reasons)
            merged_df.at[index, 'validation_status'] = 'INVALID'
        else:
            merged_df.at[index, 'validation_result'] = 'Match'
    # Select and reorder relevant columns for the report
    report_columns = [
        'file_name',
        'invoice_number_inv',
        'order_id',
        'customer_name',
        'due_date',
        'ship_to',
        'discount',
        'shipping_cost',
        'total',
        'quantity_inv',
        'quantity_po',
        'rate_inv',
        'rate_po',
        'amount',
        'expected_amount',
        'validation_result',
        'validation_status'
    ]
    validation_report_df = merged_df[report_columns]
    return validation_report_df