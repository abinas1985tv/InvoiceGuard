import pandas as pd
from utils.gemini_client import get_model 

# Expose get_model at module level for testing
model = get_model()

    
def summarize_regions(region_df: pd.DataFrame) -> dict:
    """
    Generate a structured summary of sales and shipping by region.
    Input: DataFrame with columns — region, total_sales, total_shipping, num_invoices
    Output: Dictionary with 'summary' and 'insight' fields.
    """
     
    # Prepare the prompt for the GenAI model
    prompt = (
        "Given the following regional sales data, generate key points for summary and overall insight JSON format only:\n\n"
        f"{region_df.to_dict(orient='records')}\n\n"
        "JSON Response:\n"
        "{\n"
        '  "summary": [\n'
        '    "Region A has the highest total sales...",\n'
        '    "Region B recorded the lowest shipping costs...",\n'
        '    "Region C had the fewest invoices..."\n'
        '  ],\n'
        '  "insight": "Overall, regional performance is strongest in the West due to higher volume and efficient shipping."\n'
        "}\n"
)
    
    response = model.generate_content(prompt)
    
    if response is None:
        raise RuntimeError("Failed to generate regional summary after multiple attempts.")
    
    # Get the text from the response
    response_text = response.text if hasattr(response, 'text') else str(response)
    
    # Parse the response to get the JSON string
    json_output = response_text.strip()
    # Clean up the JSON output (remove any markdown formatting if present)
    if json_output.startswith('```json'):
        json_output = json_output.replace('```json', '').replace('```', '').strip()
    elif json_output.startswith('```'):
        json_output = json_output.replace('```', '').strip()

    # Assuming the response is in JSON format
    import json
    try:
        summary_dict = json.loads(json_output)
    except json.JSONDecodeError:
        raise ValueError("Generated content is not valid JSON.")
    
    return summary_dict