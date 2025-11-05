import os
import importlib
import inspect
import re
import pandas as pd
from unittest.mock import patch, MagicMock
import streamlit.testing.v1 as st_test

# -------------------------------
# Test 1: Directory & Function Structure
# -------------------------------
def test_required_directories_and_functions():
    assert os.path.isdir("genAI")
    assert os.path.isdir("utils")

    required_functions = {
        "genAI.parser": "parse_invoice_with_genai",
        "genAI.justification": "generate_payment_justification",
        "genAI.risk_recommender": "generate_risk_recommendation",
        "genAI.region_summarizer": "summarize_regions",
        "utils.pdf_extractor": "extract_raw_text",
        "utils.payment_engine": "trigger_payment",
        "utils.validation": "validate_invoices",
    }

    for module_path, func_name in required_functions.items():
        mod = importlib.import_module(module_path)
        assert hasattr(mod, func_name), f"{func_name} missing in {module_path}"
        assert inspect.isfunction(getattr(mod, func_name))


# -------------------------------
# Test 2: GenAI Modules Return Types
# -------------------------------

@patch("genAI.parser.model.generate_content")
def test_parse_invoice_with_genai(mock_model):
    mock_model.return_value.text = '{"invoice_number": "123", "item_details": [{"item_name": "Test", "quantity": 1, "rate": 100.0, "amount": 100.0}]}'
    from genAI import parser
    result = parser.parse_invoice_with_genai("raw invoice text")
    assert isinstance(result, dict)

@patch("genAI.justification.model.generate_content")
def test_generate_payment_justification(mock_model):
    mock_model.return_value.text = "Payment of $100.00 approved for John."
    from genAI import justification
    result = justification.generate_payment_justification({
        "order_id": "O1", "customer_name": "John", "amount": 100.0, "due_date": "2025-08-06"
    })
    assert isinstance(result, str)

@patch("genAI.risk_recommender.model.generate_content")
def test_generate_risk_recommendation(mock_model):
    mock_model.return_value.text = '{"recommendation": "Escalate", "reason": "Overbilling detected"}'
    from genAI import risk_recommender
    result = risk_recommender.generate_risk_recommendation({
        "order_id": "OID1", "customer_name": "Alice", "amount": 500.0,
        "due_date": "2025-08-06", "validation_result": "Overbilling"
    })
    assert isinstance(result, dict)
    assert "recommendation" in result and "reason" in result

@patch("genAI.region_summarizer.model.generate_content")
def test_summarize_regions(mock_model):
    mock_model.return_value.text = '{"summary": ["West has highest sales"], "insight": "West region is dominant"}'
    from genAI import region_summarizer
    df = pd.DataFrame([{"region": "West", "total_sales": 10000, "total_shipping": 500, "num_invoices": 10}])
    result = region_summarizer.summarize_regions(df)
    assert isinstance(result, dict)
    assert "summary" in result and isinstance(result["summary"], list)
    assert "insight" in result


# -------------------------------
# Test 3: Payment Engine Mocked Call
# -------------------------------

@patch("utils.payment_engine.requests.post")
def test_trigger_payment(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "transaction_id": "TXN-12345",
        "status": "SUCCESS",
        "timestamp": "2025-08-06T00:00:00Z",
        "message": "Test payment successful"
    }
    from utils.payment_engine import trigger_payment
    result = trigger_payment("OID-001", "Derek", 250.0, "2025-08-06")
    assert isinstance(result, dict)
    assert result["status"] == "SUCCESS"
    assert "transaction_id" in result and "timestamp" in result


# -------------------------------
# Test 4: Streamlit UI - Tab Rendering & Plot
# -------------------------------

def test_ui_tabs_and_graphs():
    with open("main.py", "r", encoding="utf-8") as f:
        code = f.read()

    tab_match = re.search(r'st\.tabs\s*\(\s*\[(.*?)\]\s*\)', code, re.DOTALL)
    assert tab_match, "No st.tabs([...]) declaration found in main.py"

    tab_contents = tab_match.group(1)
    tab_titles = re.findall(r'"(.*?)"|\'(.*?)\'', tab_contents)
    tab_titles = [t[0] or t[1] for t in tab_titles]
    cleaned_titles = [t.strip() for t in tab_titles]

    required_tabs = {"Invoice Table", "Today's Orders", "Global Metrics"}
    assert required_tabs.issubset(set(cleaned_titles)), f"Missing tabs: expected {required_tabs}, found {cleaned_titles}"

    chart_calls = [
        "st.plotly_chart",
        "st.bar_chart",
        "st.altair_chart",
        "st.pyplot"
    ]
    chart_used = any(call in code for call in chart_calls)

    assert chart_used, "No chart function (plotly, bar, altair, pyplot) found in main.py"
