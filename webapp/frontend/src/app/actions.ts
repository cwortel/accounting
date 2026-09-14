"use server";

import { revalidatePath } from "next/cache";

import { api } from "@/lib/api";

export async function createExpenseAction(data: {
  naam: string;
  factuur?: string;
  datum: string;
  categorie: string;
  btw_pct: number;
  total: number;
  jaar: number;
  kwartaal: number;
  betaal_bron?: string;
}) {
  const expense = await api.expenses.create({
    naam: data.naam,
    factuur: data.factuur ?? "",
    datum: data.datum,
    categorie: data.categorie,
    btw_pct: data.btw_pct,
    total: data.total,
    jaar: data.jaar,
    kwartaal: data.kwartaal,
    betaal_bron: data.betaal_bron ?? "",
  });
  revalidatePath("/");
  revalidatePath("/business/expenses");
  return expense;
}

export async function deleteExpenseAction(id: number) {
  await api.expenses.remove(id);
  revalidatePath("/");
  revalidatePath("/business/expenses");
}

export async function updateExpenseAction(
  id: number,
  data: {
    naam: string;
    factuur?: string;
    datum: string;
    categorie: string;
    btw_pct: number;
    total: number;
    jaar: number;
    kwartaal: number;
    afgerekend?: boolean;
    betaal_bron?: string;
  }
) {
  const expense = await api.expenses.update(id, {
    naam: data.naam,
    factuur: data.factuur ?? "",
    datum: data.datum,
    categorie: data.categorie,
    btw_pct: data.btw_pct,
    total: data.total,
    jaar: data.jaar,
    kwartaal: data.kwartaal,
    afgerekend: data.afgerekend ?? false,
    betaal_bron: data.betaal_bron ?? "",
  });
  revalidatePath("/");
  revalidatePath("/business/expenses");
  return expense;
}

export async function createIncomeAction(data: {
  naam: string;
  factuur?: string;
  datum: string;
  project?: string;
  btw_pct: number;
  total: number;
  jaar: number;
  kwartaal: number;
}) {
  const income = await api.income.create({
    naam: data.naam,
    factuur: data.factuur ?? "",
    datum: data.datum,
    project: data.project ?? "",
    btw_pct: data.btw_pct,
    total: data.total,
    jaar: data.jaar,
    kwartaal: data.kwartaal,
  });
  revalidatePath("/");
  revalidatePath("/business/income");
  return income;
}

export async function deleteIncomeAction(id: number) {
  await api.income.remove(id);
  revalidatePath("/");
  revalidatePath("/business/income");
}

export async function updateIncomeAction(
  id: number,
  data: {
    naam: string;
    factuur?: string;
    datum: string;
    project?: string;
    btw_pct: number;
    total: number;
    jaar: number;
    kwartaal: number;
    betaald?: boolean;
  }
) {
  const income = await api.income.update(id, {
    naam: data.naam,
    factuur: data.factuur ?? "",
    datum: data.datum,
    project: data.project ?? "",
    btw_pct: data.btw_pct,
    total: data.total,
    jaar: data.jaar,
    kwartaal: data.kwartaal,
    betaald: data.betaald ?? false,
  });
  revalidatePath("/");
  revalidatePath("/business/income");
  return income;
}

export async function linkTransactionAction(txId: number, expenseId: number, fooi: number) {
  await api.bank.link(txId, { expense_id: expenseId, fooi });
  revalidatePath("/business/transactions");
}

export async function linkIncomeTransactionAction(txId: number, incomeId: number) {
  await api.bank.link(txId, { income_id: incomeId });
  revalidatePath("/business/transactions");
}

export async function getMatchCandidatesAction(txId: number) {
  return api.bank.matchCandidates(txId);
}

export async function getIncomeMatchCandidatesAction(txId: number) {
  return api.bank.incomeMatchCandidates(txId);
}

export async function unlinkTransactionAction(txId: number) {
  await api.bank.unlink(txId);
  revalidatePath("/business/transactions");
}

export async function markPriveAction(txId: number, omschrijving: string) {
  await api.bank.markPrive(txId, omschrijving);
  revalidatePath("/business/transactions");
}

export async function markInternAction(txId: number, omschrijving: string) {
  await api.bank.markIntern(txId, omschrijving);
  revalidatePath("/business/transactions");
}

export async function markBtwBetalingAction(txId: number, jaar: number, kwartaal: number) {
  await api.bank.markBtwBetaling(txId, jaar, kwartaal);
  revalidatePath("/business/transactions");
}

export async function createExpenseFromTxAction(
  txId: number,
  data: { categorie: string; btw_pct?: number; factuur?: string; naam?: string; notitie?: string }
) {
  const expense = await api.bank.createExpenseFromTx(txId, data);
  revalidatePath("/business/transactions");
  revalidatePath("/business/expenses");
  return expense;
}

export async function importBankFileAction(formData: FormData) {
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    throw new Error("Geen bestand geselecteerd");
  }
  const result = file.name.toLowerCase().endsWith(".csv")
    ? await api.bank.importRabobankCsv(file)
    : await api.bank.importCamt(file);
  revalidatePath("/business/transactions");
  revalidatePath("/business/accounts");
  return result;
}

export async function importScanFolderAction() {
  const results = await api.bank.importScanFolder();
  revalidatePath("/business/transactions");
  revalidatePath("/business/accounts");
  return results;
}

export async function createDebtAction(data: {
  naam: string;
  partij?: string;
  iban?: string;
  origineel_bedrag: number;
  termijn_bedrag: number;
  frequentie: string;
  start_datum?: string;
  aantal_termijnen?: number;
  betaald_termijnen?: number;
  extra_betaald?: number;
  actief?: boolean;
  notities?: string;
}) {
  const debt = await api.private.debts.create(data);
  revalidatePath("/private/debts");
  return debt;
}

export async function updateDebtAction(
  id: number,
  data: {
    naam: string;
    partij?: string;
    iban?: string;
    origineel_bedrag: number;
    termijn_bedrag: number;
    frequentie: string;
    start_datum?: string;
    aantal_termijnen?: number;
    betaald_termijnen?: number;
    extra_betaald?: number;
    actief?: boolean;
    notities?: string;
  }
) {
  const debt = await api.private.debts.update(id, data);
  revalidatePath("/private/debts");
  return debt;
}

export async function deleteDebtAction(id: number) {
  await api.private.debts.remove(id);
  revalidatePath("/private/debts");
}

export async function createAccountAction(data: {
  naam: string;
  iban: string;
  type: string;
  categorie: string;
  saldo?: number;
}) {
  const account = await api.accounts.create(data);
  revalidatePath("/business/accounts");
  return account;
}

export async function updateAccountAction(
  id: number,
  data: { naam: string; iban: string; type: string; categorie: string; saldo?: number }
) {
  const account = await api.accounts.update(id, data);
  revalidatePath("/business/accounts");
  return account;
}

export async function deleteAccountAction(id: number) {
  await api.accounts.remove(id);
  revalidatePath("/business/accounts");
}

export async function setSettingAction(key: string, value: string) {
  return api.settings.set(key, value);
}

export async function setPriveCategorieAction(txId: number, categorie: string, applyToNaam: boolean) {
  const result = await api.private.setCategorie(txId, categorie, applyToNaam);
  revalidatePath("/private");
  return result;
}

export async function setPriveRecurringAction(txId: number, isRecurring: boolean, applyToNaam: boolean) {
  const result = await api.private.setRecurring(txId, isRecurring, applyToNaam);
  revalidatePath("/private");
  return result;
}

