"""Rule-based checks on extracted invoice JSON (no API needed).

Each check returns {"status": "PASS" | "CHECK", "message": str}.
"""
import re

REQUIRED = ["vendor", "invoice", "items", "subtotal", "tax_amount", "additional_charges",
            "total_amount", "amount_due", "uncertain_fields"]
TOLERANCE = 1.0  # allow small rounding differences


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check(ok, pass_msg, check_msg):
    return {"status": "PASS" if ok else "CHECK", "message": pass_msg if ok else check_msg}


def validate_invoice_json(data):
    if not isinstance(data, dict):
        return [_check(False, "", "Output is not a JSON object.")]

    out = []
    missing = [k for k in REQUIRED if k not in data]
    out.append(_check(not missing, "All required top-level fields present.",
                      "Missing keys: " + ", ".join(missing)))

    items = data.get("items")
    out.append(_check(isinstance(items, list), "items is a list.", "items must be a list."))

    # Line-level arithmetic: qty x price (minus discount) vs line_total
    problems, line_totals = [], []
    for i, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            problems.append(f"Item {i+1} is not an object.")
            continue
        q, p, t = item.get("quantity"), item.get("unit_price"), item.get("line_total")
        d = item.get("discount") if _num(item.get("discount")) else 0
        if _num(t):
            line_totals.append(t)
        if _num(q) and _num(p) and _num(t):
            expected = q * p - d
            if abs(expected - t) > TOLERANCE and abs(q * p - t) > TOLERANCE:
                problems.append(f"Item {i+1}: qty x price - discount = {expected:g}, "
                                f"but line total is {t:g} (tax-inclusive pricing may explain it).")
    out.append(_check(not problems, "Line items: no arithmetic mismatch found.", " ".join(problems)))

    sub = data.get("subtotal")
    if _num(sub) and line_totals and len(line_totals) == len(items):
        s = sum(line_totals)
        out.append(_check(abs(s - sub) <= TOLERANCE, f"Sum of line totals matches subtotal ({sub:g}).",
                          f"Sum of line totals ({s:g}) differs from subtotal ({sub:g})."))

    tax, chg, tot = data.get("tax_amount"), data.get("additional_charges"), data.get("total_amount")
    if _num(sub) and _num(tot):
        exp = sub + (tax if _num(tax) else 0) + (chg if _num(chg) else 0)
        out.append(_check(abs(exp - tot) <= TOLERANCE,
                          f"subtotal + tax + charges matches total ({tot:g}).",
                          f"subtotal + tax + charges = {exp:g}, but printed total is {tot:g}."))

    due = data.get("amount_due")
    if _num(due) and _num(tot) and due > tot + TOLERANCE:
        out.append(_check(False, "", f"Amount due ({due:g}) is greater than total ({tot:g})."))

    inv = data.get("invoice") if isinstance(data.get("invoice"), dict) else {}
    bad_dates = [k for k in ("date", "due_date")
                 if inv.get(k) is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(inv.get(k)))]
    out.append(_check(not bad_dates, "Dates are YYYY-MM-DD or null.",
                      "Dates not in YYYY-MM-DD: " + ", ".join(bad_dates)))

    vendor = data.get("vendor") if isinstance(data.get("vendor"), dict) else {}
    gstin = vendor.get("gstin")
    if gstin:
        ok = bool(re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]", str(gstin).upper()))
        out.append(_check(ok, "GSTIN format looks valid.", f"GSTIN '{gstin}' does not match the 15-character format."))

    u = data.get("uncertain_fields", [])
    out.append(_check(isinstance(u, list), f"{len(u) if isinstance(u, list) else 0} uncertain field(s) flagged.",
                      "uncertain_fields must be a list."))
    return out
