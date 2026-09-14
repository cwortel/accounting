from datetime import date

from pydantic import BaseModel, ConfigDict


class ExpenseBase(BaseModel):
    factuur: str = ""
    naam: str = ""
    datum: date | None = None
    categorie: str = ""
    btw_pct: int = 0
    total: float = 0
    afgerekend: bool = False
    betaal_bron: str = ""
    jaar: int
    kwartaal: int


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    pass


class Expense(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    btw: float = 0
    ex_btw: float = 0


class ExpenseQuickCapture(BaseModel):
    """Minimal payload for fast capture, e.g. from a mobile OCR app."""

    naam: str = ""
    datum: date | None = None
    total: float
    btw_pct: int = 0
    categorie: str = ""
    factuur: str = ""
    betaal_bron: str = ""


class IncomeBase(BaseModel):
    factuur: str = ""
    naam: str = ""
    datum: date | None = None
    project: str = ""
    btw_pct: int = 21
    total: float = 0
    betaald: bool = False
    jaar: int
    kwartaal: int


class IncomeCreate(IncomeBase):
    pass


class IncomeUpdate(IncomeBase):
    pass


class Income(IncomeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    btw: float = 0
    ex_btw: float = 0


class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    naam: str


class RekeningBase(BaseModel):
    naam: str = ""
    iban: str = ""
    type: str = "prive"
    categorie: str = "betaalrekening"
    saldo: float = 0
    laatste_update: date | None = None


class RekeningCreate(RekeningBase):
    pass


class Rekening(RekeningBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class BankTransaction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    datum: date
    bedrag: float
    naam: str = ""
    iban: str = ""
    referentie: str = ""
    bestand: str = ""
    jaar: int
    kwartaal: int
    expense_id: int | None = None
    income_id: int | None = None
    fooi: float = 0
    prive: bool = False
    prive_omschrijving: str = ""
    rekening: str = ""
    saldo_na_trn: float | None = None
    prive_categorie: str = ""
    is_recurring: bool = False
    intern: bool = False
    intern_omschrijving: str = ""
    btw_betaling: bool = False
    btw_betaling_jaar: int | None = None
    btw_betaling_kwartaal: int | None = None


class LinkBankTransaction(BaseModel):
    expense_id: int | None = None
    income_id: int | None = None
    fooi: float = 0


class MarkPrive(BaseModel):
    omschrijving: str = ""


class MarkIntern(BaseModel):
    omschrijving: str = ""


class MarkBtwBetaling(BaseModel):
    jaar: int
    kwartaal: int


class CreateExpenseFromBank(BaseModel):
    categorie: str
    btw_pct: int = 0
    factuur: str = ""
    naam: str = ""
    notitie: str = ""


class MatchCandidate(BaseModel):
    expense_id: int
    naam: str
    datum: date | None = None
    total: float
    score: int
    fooi: float = 0


class IncomeMatchCandidate(BaseModel):
    income_id: int
    naam: str
    datum: date | None = None
    total: float
    score: int


class ImportResult(BaseModel):
    bestand: str
    aantal_toegevoegd: int


class YearlyQuarterSummary(BaseModel):
    kwartaal: int
    omzet: float
    kosten: float
    winst: float
    btw_in: float
    btw_uit: float
    btw_saldo: float


class CategoryQuarterBreakdown(BaseModel):
    categorie: str
    q1: float
    q2: float
    q3: float
    q4: float
    totaal: float


class SchuldBase(BaseModel):
    naam: str = ""
    partij: str = ""
    iban: str = ""
    origineel_bedrag: float = 0
    termijn_bedrag: float = 0
    frequentie: str = "maandelijks"
    start_datum: date | None = None
    aantal_termijnen: int = 0
    betaald_termijnen: int = 0
    extra_betaald: float = 0
    betaaldatum: date | None = None
    actief: bool = True
    notities: str = ""


class SchuldCreate(SchuldBase):
    pass


class Schuld(SchuldBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    huidig_restant: float = 0


class SettingValue(BaseModel):
    value: str


class MonthlyCashflow(BaseModel):
    maand: str  # "YYYY-MM"
    omzet: float = 0
    kosten: float = 0
    prive_out: float = 0
    btw_paid: float = 0
    recurring_prive: float = 0
    totaal_prive_uitgaven: float = 0
