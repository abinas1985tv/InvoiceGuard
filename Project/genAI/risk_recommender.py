from utils.gemini_client import get_model 

# Expose get_model at module level for testing
model = get_model()

def generate_risk_recommendation(invoice_row: dict) -> dict:
    """
    Ask GenAI whether to escalate, approve, or hold a mismatched invoice due today.
    Returns a dictionary with keys: 'recommendation' and 'reason'.
    """
        
    prompt = (
        f"An invoice is marked as INVALID due to the following reason: {invoice_row['validation_result']}.\n"
        f"The invoice details are:\n"
        f"Order ID: {invoice_row['order_id']}\n"
        f"Customer Name: {invoice_row['customer_name']}\n"
        f"Amount: ${invoice_row['amount']:.2f}\n"
        f"Due Date: {invoice_row['due_date']} (today)\n\n"
        "Based on this information, provide a recommendation to either 'Approve', 'Escalate', or 'Hold' the invoice. "
        "Also provide a brief reason for your recommendation in the following JSON format:\n"
        "{\n"
        '"recommendation": "<Approve/Escalate/Hold>",\n'
        '"reason": "<brief explanation>"\n'
        "}"
    )
    #print(f"Generated Prompt for Gemini:\n{prompt}\n")
    response = model.generate_content(prompt)
    
    #print(f"Gemini Response:\n{response}\n")
    if response is None:
        raise ValueError("Failed to get response from Gemini API.") 

    # Get the text from the response
    response_text = response.text if hasattr(response, 'text') else str(response)
    
    json_output = response_text.strip()
    # Clean up the JSON output (remove any markdown formatting if present)
    if json_output.startswith('```json'):
        json_output = json_output.replace('```json', '').replace('```', '').strip()
    elif json_output.startswith('```'):
        json_output = json_output.replace('```', '').strip()

    # Assuming the response is in JSON format
    import json
    try:
        recommendation_dict = json.loads(json_output)
    except json.JSONDecodeError:
        raise ValueError("Generated content is not valid JSON.")
    
    return recommendation_dict