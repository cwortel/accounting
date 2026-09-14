from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    naam: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    factuur: Mapped[str] = mapped_column(String, default="")
    naam: Mapped[str] = mapped_column(String, default="")
    datum: Mapped[str] = mapped_column(String, default="")
    categorie: Mapped[str] = mapped_column(String, default="")
    btw_pct: Mapped[int] = mapped_column(Integer, default=0)
    btw: Mapped[float] = mapped_column(Float, default=0)
    ex_btw: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    afgerekend: Mapped[bool] = mapped_column(Boolean, default=False)
    betaal_bron: Mapped[str] = mapped_column(String, default="")
    jaar: Mapped[int] = mapped_column(Integer, nullable=False)
    kwartaal: Mapped[int] = mapped_column(Integer, nullable=False)


class Income(Base):
    __tablename__ = "income"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    factuur: Mapped[str] = mapped_column(String, default="")
    naam: Mapped[str] = mapped_column(String, default="")
    datum: Mapped[str] = mapped_column(String, default="")
    project: Mapped[str] = mapped_column(String, default="")
    btw_pct: Mapped[int] = mapped_column(Integer, default=21)
    btw: Mapped[float] = mapped_column(Float, default=0)
    ex_btw: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    betaald: Mapped[bool] = mapped_column(Boolean, default=False)
    jaar: Mapped[int] = mapped_column(Integer, nullable=False)
    kwartaal: Mapped[int] = mapped_column(Integer, nullable=False)


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    datum: Mapped[str] = mapped_column(String, nullable=False)
    bedrag: Mapped[float] = mapped_column(Float, nullable=False)
    naam: Mapped[str] = mapped_column(String, default="")
    iban: Mapped[str] = mapped_column(String, default="")
    referentie: Mapped[str] = mapped_column(String, default="")
    bestand: Mapped[str] = mapped_column(String, default="")
    jaar: Mapped[int] = mapped_column(Integer, nullable=False)
    kwartaal: Mapped[int] = mapped_column(Integer, nullable=False)
    expense_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    income_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fooi: Mapped[float] = mapped_column(Float, default=0)
    prive: Mapped[bool] = mapped_column(Boolean, default=False)
    prive_omschrijving: Mapped[str] = mapped_column(String, default="")
    rekening: Mapped[str] = mapped_column(String, default="")
    saldo_na_trn: Mapped[float | None] = mapped_column(Float, nullable=True)
    code: Mapped[str] = mapped_column(String, default="")
    machtigingskenmerk: Mapped[str] = mapped_column(String, default="")
    incassant_id: Mapped[str] = mapped_column(String, default="")
    # Bank-assigned stable reference (CAMT NtryRef / CSV Volgnr) — the authoritative
    # dedup key, robust against overlapping exports. Empty for legacy CSV rows,
    # which already dedupe via `referentie` (their volgnr) instead.
    bank_ref: Mapped[str] = mapped_column(String, default="")
    prive_categorie: Mapped[str] = mapped_column(String, default="")
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    intern: Mapped[bool] = mapped_column(Boolean, default=False)
    intern_omschrijving: Mapped[str] = mapped_column(String, default="")
    btw_betaling: Mapped[bool] = mapped_column(Boolean, default=False)
    btw_betaling_jaar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    btw_betaling_kwartaal: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Rekening(Base):
    __tablename__ = "rekeningen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    naam: Mapped[str] = mapped_column(String, default="")
    iban: Mapped[str] = mapped_column(String, unique=True, default="")
    type: Mapped[str] = mapped_column(String, default="prive")
    categorie: Mapped[str] = mapped_column(String, default="betaalrekening")
    saldo: Mapped[float] = mapped_column(Float, default=0)
    laatste_update: Mapped[str] = mapped_column(String, default="")


class Schuld(Base):
    __tablename__ = "schulden"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    naam: Mapped[str] = mapped_column(String, default="")
    partij: Mapped[str] = mapped_column(String, default="")
    iban: Mapped[str] = mapped_column(String, default="")
    origineel_bedrag: Mapped[float] = mapped_column(Float, default=0)
    huidig_restant: Mapped[float] = mapped_column(Float, default=0)
    termijn_bedrag: Mapped[float] = mapped_column(Float, default=0)
    frequentie: Mapped[str] = mapped_column(String, default="maandelijks")
    start_datum: Mapped[str] = mapped_column(String, default="")
    aantal_termijnen: Mapped[int] = mapped_column(Integer, default=0)
    betaald_termijnen: Mapped[int] = mapped_column(Integer, default=0)
    extra_betaald: Mapped[float] = mapped_column(Float, default=0)
    betaaldatum: Mapped[str] = mapped_column(String, default="")
    actief: Mapped[bool] = mapped_column(Boolean, default=True)
    notities: Mapped[str] = mapped_column(String, default="")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, default="")
