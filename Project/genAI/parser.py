import os
import csv
import json
import time
from typing import List, Optional
from utils.gemini_client import get_model

# Use the shared model from gemini_client
model = get_model()

def parse_invoice_with_genai(text: str) -> dict:

    # Define the prompt for the Gemini model

    prompt = f"""
You are an expert invoice data extraction system. Extract the following fields from the invoice text and return ONLY a valid JSON object.
EXTRACTION RULES:
1-customer_name: Extract from the "Bill To" or "Billing Address" section - get the company/person name only
2-every item_name is in multiple lines. Make sure to extract full text for item_name.example:"EplettSuperStoreItemCanon Wireless Fax, LaserCopiers, Technology, TEC-CO-3710Notes".
3-Do not include any zero quantity items in item_details.
Invoice Text:
{text}
JSON Response:
{{
    "invoice_number": "...",
    "order_id": "...",
    "customer_name": "...",
    "due_date": "...",
    "ship_to": "...",
    "ship_mode": "...",
    "subtotal": 0.0,
    "discount": 0.0,
    "shipping_cost": 0.0,
    "total": 0.0,
    "item_details": [
        {{
            "item_name": "...",
            "quantity": 0,
            "rate": 0.0,
            "amount": 0.0
        }}
    ]
}}
    """

    # Call the Gemini API with multi-key support
    response = model.generate_content(prompt)
    #Incase of failure to get response, return None so that it can be handled upstream
    if response is None:
        invoice_data = None
        return invoice_data
    
    # Get the text from the response
    response_text = response.text if hasattr(response, 'text') else str(response)
    
    # Parse the response to get the JSON string
    json_output = response_text.strip()
    
    # Clean up the JSON output (remove any markdown formatting if present)
    if json_output.startswith('```json'):
        json_output = json_output.replace('```json', '').replace('```', '').strip()
    elif json_output.startswith('```'):
        json_output = json_output.replace('```', '').strip()

    try:
        # Convert the JSON string to a Python dictionary
        invoice_data = json.loads(json_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response from Gemini API: {e}")

    return invoice_data
