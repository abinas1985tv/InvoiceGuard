import requests
def trigger_payment(order_id: str, customer_name: str, amount: float, due_date: str) -> dict:
    """
    Sends payment initiation request to local FastAPI endpoint.
    Returns a dictionary with transaction details and status.
    """
    url = "http://localhost:8000/initiate_payment"
    payload = {
        "order_id": order_id,
        "customer_name": customer_name,
        "amount": amount,
        "due_date": due_date
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an error for bad status codes
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Payment initiation failed: {e}") from e