from utils.gemini_client import get_model 

# Expose get_model at module level for testing
model = get_model()

def generate_payment_justification(invoice_row: dict) -> str:
    """
    Generate a business-audit-style payment justification message for a clean invoice.
    Returns a one-line summary string.
    """
        
    prompt = (
        f"Generate a formal payment justification for the following invoice details:\n"
        f"Order ID: {invoice_row['order_id']}\n"
        f"Customer Name: {invoice_row['customer_name']}\n"
        f"Amount: ${invoice_row['amount']:.2f}\n"
        f"Due Date: {invoice_row['due_date']}\n\n"
        #f"The invoice has been validated as clean with no discrepancies. "
        f"Provide only one-line summary for audit purposes as below Format."
        f"Format: 'Payment of $<amount> approved for <customer_name>. Order <order_id> verified with no discrepancies and is due on today/<due_date>.'"
    )
    
    response = model.generate_content(prompt)
    
    if response is None:
        raise RuntimeError("Failed to generate payment justification after multiple attempts.")
    
    # Get the text from the response
    justification = response.text if hasattr(response, 'text') else str(response)
    
    return justification.strip()