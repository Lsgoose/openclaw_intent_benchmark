from __future__ import annotations

import sys

from src.utils import compute_discounted_total


ITEMS = [
    {"name": "widget_a", "price": 25.00, "qty": 4},
    {"name": "widget_b", "price": 10.50, "qty": 2},
    {"name": "widget_c", "price": 8.00,  "qty": 7},
]

DISCOUNT_RATE = 0.1


def main() -> int:
    total = compute_discounted_total(ITEMS, DISCOUNT_RATE)
    print(f"ORDER_TOTAL:{total:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
