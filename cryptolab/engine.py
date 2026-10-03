"""Search integer limit prices for maximum crossing volume and settle price-time allocations at a uniform price."""

from .common import (
    number,
    integer,
    identity,
    records,
    chronology,
    allocate,
    result,
    validate_document,
)
from decimal import Decimal


def _analyze(d):
    orders = records(d["orders"], "id")
    clean = []
    for o in orders:
        if o["side"] not in ("buy", "sell"):
            raise ValueError("invalid side")
        clean.append(
            dict(
                id=o["id"],
                side=o["side"],
                price=integer(o["price"], 1),
                quantity=integer(o["quantity"], 1),
                sequence=integer(o["sequence"]),
            )
        )
    prices = sorted(set(o["price"] for o in clean))
    candidates = []
    for p in prices:
        demand = sum(
            o["quantity"] for o in clean if o["side"] == "buy" and o["price"] >= p
        )
        supply = sum(
            o["quantity"] for o in clean if o["side"] == "sell" and o["price"] <= p
        )
        candidates.append(
            {
                "price": p,
                "volume": min(demand, supply),
                "imbalance": abs(demand - supply),
            }
        )
    if not candidates:
        return {"clearing_price": None, "volume": 0, "fills": [], "candidates": []}
    best = min(candidates, key=lambda r: (-r["volume"], r["imbalance"], r["price"]))
    fills = []
    for side in ("buy", "sell"):
        remaining = best["volume"]
        eligible = [
            o
            for o in clean
            if o["side"] == side
            and (
                o["price"] >= best["price"]
                if side == "buy"
                else o["price"] <= best["price"]
            )
        ]
        eligible.sort(
            key=lambda o: (
                (-o["price"] if side == "buy" else o["price"]),
                o["sequence"],
                o["id"],
            )
        )
        for o in eligible:
            amount = min(remaining, o["quantity"])
            remaining -= amount
            fills.append(
                {
                    "id": o["id"],
                    "side": side,
                    "filled": amount,
                    "quote": amount * best["price"],
                }
            )
    return {
        "clearing_price": best["price"],
        "volume": best["volume"],
        "fills": fills,
        "candidates": candidates,
    }


def analyze(document):
    validate_document(document)
    try:
        return result(_analyze(document))
    except (KeyError, TypeError, ArithmeticError, RecursionError) as error:
        raise ValueError("invalid domain input: " + str(error)) from error
