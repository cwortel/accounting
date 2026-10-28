"""Small shared business rule for expenses, used by both manual entry and receipt approval."""

# Payment methods that will never produce a matching business bank transaction —
# an expense paid this way should be considered settled immediately rather than
# waiting indefinitely for a bank-transaction link that will never come.
_NO_BANK_MATCH_SOURCES = {"Privé rekening", "Privé creditcard", "Contant"}


def auto_voldaan(betaal_bron: str) -> bool:
    return betaal_bron in _NO_BANK_MATCH_SOURCES
