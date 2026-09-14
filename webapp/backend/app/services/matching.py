"""Scores existing expenses as match candidates for an unlinked bank transaction.

Ported from the Streamlit page's inline matching logic (pages/2_Zakelijke_Transacties.py)
so both the API and any future client share identical matching behaviour.
"""

from datetime import date

from .. import models


def score_expense(expense: models.Expense, amt: float, tx_datum: date, tx_naam: str, tx_ref: str) -> int:
    exp_total = float(expense.total or 0)
    if exp_total <= 0:
        return -1
    ratio = amt / exp_total
    # Disqualify: bank paid less than 95% or tip would exceed 25%
    if ratio < 0.95 or ratio > 1.25:
        return -1

    score = 0
    near_exact_amount = ratio <= 1.005

    if near_exact_amount:
        score += 10
    elif ratio <= 1.10:
        score += 6
    elif ratio <= 1.20:
        score += 2

    days = None
    try:
        exp_date = date.fromisoformat(str(expense.datum)[:10])
        days = abs((tx_datum - exp_date).days)
        if days == 0:
            score += 10
        elif days <= 2:
            score += 7
        elif days <= 7:
            score += 3
        elif days <= 14:
            score += 1
    except (ValueError, TypeError):
        pass

    hay = (str(tx_naam) + " " + str(tx_ref)).lower()
    exp_naam = str(expense.naam or "").lower().strip()
    name_score = 0
    if exp_naam and exp_naam in hay:
        name_score = 10
    else:
        words = sorted([w for w in exp_naam.split() if len(w) >= 4], key=len, reverse=True)
        if words and words[0] in hay:
            name_score = 5
    score += name_score

    if days is not None and days > 14:
        if near_exact_amount and name_score >= 5 and days <= 35:
            score += 1 if days <= 21 else 0
        else:
            return -1

    return score


def score_income(income: models.Income, amt: float, tx_datum: date, tx_naam: str, tx_ref: str) -> int:
    inc_total = float(income.total or 0)
    if inc_total <= 0:
        return -1
    ratio = amt / inc_total
    # Credits should be close to invoice total (no tips on income)
    if ratio < 0.95 or ratio > 1.05:
        return -1

    score = 10 if ratio <= 1.005 else 4

    try:
        inc_date = date.fromisoformat(str(income.datum)[:10])
        days = abs((tx_datum - inc_date).days)
        if days <= 7:
            score += 10
        elif days <= 30:
            score += 5
        elif days <= 60:
            score += 1
        else:
            return -1
    except (ValueError, TypeError):
        pass

    hay = (str(tx_naam) + " " + str(tx_ref)).lower()
    inc_naam = str(income.naam or "").lower().strip()
    if inc_naam and inc_naam in hay:
        score += 10
    else:
        words = sorted([w for w in inc_naam.split() if len(w) >= 4], key=len, reverse=True)
        if words and words[0] in hay:
            score += 5

    return score
