# ==================================
# DO NOT MODIFY/EDIT BELOW THIS LINE
# ==================================
from fastapi import FastAPI, Request
from pydantic import BaseModel
from datetime import datetime,timezone
import random

app = FastAPI()

class PaymentRequest(BaseModel):
    order_id: str
    customer_name: str
    amount: float
    due_date: str

@app.post("/initiate_payment")
def initiate_payment(data: PaymentRequest):
    return {
        "transaction_id": f"TXN-{random.randint(10000,99999)}",
        "status": "SUCCESS",
        #"timestamp": datetime.utcnow().isoformat(),
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "message": f"Payment triggered for {data.customer_name} (${data.amount})"
    }
