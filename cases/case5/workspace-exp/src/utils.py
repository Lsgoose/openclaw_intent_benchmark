from __future__ import annotations


def compute_discounted_total(items: list[dict], discount_rate: float) -> float:
    """Return the order total after applying a flat discount rate to the subtotal."""
    subtotal = 0.0
    for item in items:
        line = item["price"] * item["qty"]
        subtotal += line
    # Fix: apply the discount rate to the accumulated subtotal
    total = subtotal * (1 - discount_rate)
    return round(total, 2)
