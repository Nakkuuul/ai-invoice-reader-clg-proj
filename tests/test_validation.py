"""Offline tests for the rule-based validator (no API key needed). Run: python -m pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validation import validate_invoice_json  # noqa: E402

GOOD = {
    "vendor": {"name": "ABC Supplies", "address": None, "gstin": None},
    "invoice": {"number": "INV-101", "date": "2026-10-10", "due_date": None, "currency": "INR"},
    "items": [{"description": "Printer Paper", "quantity": 10, "unit_price": 200,
               "tax_rate": 18, "discount": None, "line_total": 2000}],
    "subtotal": 2000, "tax_amount": 360, "additional_charges": None,
    "total_amount": 2360, "amount_due": 2360, "uncertain_fields": [], "validation_notes": [],
}


def statuses(data):
    return [c["status"] for c in validate_invoice_json(data)]


def test_clean_invoice_passes():
    assert set(statuses(GOOD)) == {"PASS"}


def test_line_mismatch_flagged():
    bad = {**GOOD, "items": [{**GOOD["items"][0], "line_total": 1800}]}
    assert "CHECK" in statuses(bad)


def test_total_mismatch_flagged():
    assert "CHECK" in statuses({**GOOD, "total_amount": 2500, "amount_due": 2500})


def test_bad_date_flagged():
    assert "CHECK" in statuses({**GOOD, "invoice": {**GOOD["invoice"], "date": "10/10/2026"}})


def test_missing_keys_and_non_dict():
    assert "CHECK" in statuses({"vendor": {}})
    assert statuses([]) == ["CHECK"]
