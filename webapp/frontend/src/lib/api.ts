import "server-only";

const BASE_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const API_KEY = process.env.BACKEND_API_KEY ?? "";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "X-API-Key": API_KEY,
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Expense = {
  id: number;
  factuur: string;
  naam: string;
  datum: string | null;
  categorie: string;
  btw_pct: number;
  btw: number;
  ex_btw: number;
  total: number;
  afgerekend: boolean;
  betaal_bron: string;
  jaar: number;
  kwartaal: number;
};

export type Income = {
  id: number;
  factuur: string;
  naam: string;
  datum: string | null;
  project: string;
  btw_pct: number;
  btw: number;
  ex_btw: number;
  total: number;
  betaald: boolean;
  jaar: number;
  kwartaal: number;
};

export type BankTransaction = {
  id: number;
  datum: string;
  bedrag: number;
  naam: string;
  iban: string;
  referentie: string;
  jaar: number;
  kwartaal: number;
  expense_id: number | null;
  income_id: number | null;
  fooi: number;
  prive: boolean;
  prive_omschrijving: string;
  rekening: string;
  prive_categorie: string;
  is_recurring: boolean;
  intern: boolean;
  intern_omschrijving: string;
  btw_betaling: boolean;
};

export type Rekening = {
  id: number;
  naam: string;
  iban: string;
  type: string;
  categorie: string;
  saldo: number;
  laatste_update: string | null;
};

export type YearlyQuarterSummary = {
  kwartaal: number;
  omzet: number;
  kosten: number;
  winst: number;
  btw_in: number;
  btw_uit: number;
  btw_saldo: number;
};

export type CategoryQuarterBreakdown = {
  categorie: string;
  q1: number;
  q2: number;
  q3: number;
  q4: number;
  totaal: number;
};

export type MatchCandidate = {
  expense_id: number;
  naam: string;
  datum: string | null;
  total: number;
  score: number;
  fooi: number;
};

export type IncomeMatchCandidate = {
  income_id: number;
  naam: string;
  datum: string | null;
  total: number;
  score: number;
};

export type ImportResult = {
  bestand: string;
  aantal_toegevoegd: number;
};

export type Schuld = {
  id: number;
  naam: string;
  partij: string;
  iban: string;
  origineel_bedrag: number;
  huidig_restant: number;
  termijn_bedrag: number;
  frequentie: string;
  start_datum: string | null;
  aantal_termijnen: number;
  betaald_termijnen: number;
  extra_betaald: number;
  betaaldatum: string | null;
  actief: boolean;
  notities: string;
};

export type MonthlyCashflow = {
  maand: string;
  omzet: number;
  kosten: number;
  prive_out: number;
  btw_paid: number;
  recurring_prive: number;
  totaal_prive_uitgaven: number;
};

export const api = {
  expenses: {
    list: (jaar: number, kwartaal?: number) =>
      request<Expense[]>(`/expenses?jaar=${jaar}${kwartaal ? `&kwartaal=${kwartaal}` : ""}`),
    create: (data: Partial<Expense>) =>
      request<Expense>("/expenses", { method: "POST", body: JSON.stringify(data) }),
    quickCapture: (data: { naam: string; total: number; btw_pct?: number; categorie?: string; datum?: string }) =>
      request<Expense>("/expenses/quick-capture", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Expense>) =>
      request<Expense>(`/expenses/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/expenses/${id}`, { method: "DELETE" }),
  },
  income: {
    list: (jaar: number, kwartaal?: number) =>
      request<Income[]>(`/income?jaar=${jaar}${kwartaal ? `&kwartaal=${kwartaal}` : ""}`),
    create: (data: Partial<Income>) =>
      request<Income>("/income", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Income>) =>
      request<Income>(`/income/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/income/${id}`, { method: "DELETE" }),
  },
  categories: {
    list: () => request<string[]>("/categories"),
  },
  accounts: {
    list: () => request<Rekening[]>("/accounts"),
    create: (data: Partial<Rekening>) =>
      request<Rekening>("/accounts", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Rekening>) =>
      request<Rekening>(`/accounts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/accounts/${id}`, { method: "DELETE" }),
  },
  bank: {
    list: (jaar: number, opts?: { kwartaal?: number; onlyUnmatched?: boolean; rekeningType?: string }) => {
      const params = new URLSearchParams({ jaar: String(jaar) });
      if (opts?.kwartaal) params.set("kwartaal", String(opts.kwartaal));
      if (opts?.onlyUnmatched) params.set("only_unmatched", "true");
      if (opts?.rekeningType) params.set("rekening_type", opts.rekeningType);
      return request<BankTransaction[]>(`/bank-transactions?${params}`);
    },
    matchCandidates: (txId: number) => request<MatchCandidate[]>(`/bank-transactions/${txId}/match-candidates`),
    incomeMatchCandidates: (txId: number) =>
      request<IncomeMatchCandidate[]>(`/bank-transactions/${txId}/income-match-candidates`),
    link: (txId: number, data: { expense_id?: number; income_id?: number; fooi?: number }) =>
      request<BankTransaction>(`/bank-transactions/${txId}/link`, { method: "POST", body: JSON.stringify(data) }),
    unlink: (txId: number) => request<BankTransaction>(`/bank-transactions/${txId}/unlink`, { method: "POST" }),
    markPrive: (txId: number, omschrijving = "") =>
      request<BankTransaction>(`/bank-transactions/${txId}/mark-prive`, {
        method: "POST",
        body: JSON.stringify({ omschrijving }),
      }),
    markIntern: (txId: number, omschrijving = "") =>
      request<BankTransaction>(`/bank-transactions/${txId}/mark-intern`, {
        method: "POST",
        body: JSON.stringify({ omschrijving }),
      }),
    markBtwBetaling: (txId: number, jaar: number, kwartaal: number) =>
      request<BankTransaction>(`/bank-transactions/${txId}/mark-btw-betaling`, {
        method: "POST",
        body: JSON.stringify({ jaar, kwartaal }),
      }),
    createExpenseFromTx: (
      txId: number,
      data: { categorie: string; btw_pct?: number; factuur?: string; naam?: string; notitie?: string }
    ) =>
      request<Expense>(`/bank-transactions/${txId}/create-expense`, { method: "POST", body: JSON.stringify(data) }),
    importCamt: (file: File) => {
      const form = new FormData();
      form.set("file", file);
      return request<ImportResult>("/bank-transactions/import/camt", { method: "POST", body: form });
    },
    importRabobankCsv: (file: File) => {
      const form = new FormData();
      form.set("file", file);
      return request<ImportResult>("/bank-transactions/import/rabobank-csv", { method: "POST", body: form });
    },
    importScanFolder: () =>
      request<ImportResult[]>("/bank-transactions/import/scan-folder", { method: "POST" }),
  },
  reports: {
    yearlySummary: (jaar: number) => request<YearlyQuarterSummary[]>(`/reports/yearly-summary?jaar=${jaar}`),
    expenseByCategory: (jaar: number) =>
      request<CategoryQuarterBreakdown[]>(`/reports/expense-by-category?jaar=${jaar}`),
    btwAangifte: (jaar: number) => request<Record<string, number>[]>(`/reports/btw-aangifte?jaar=${jaar}`),
    btwBetalingen: (jaar: number) =>
      request<Record<string, { tx_id: number; datum: string; bedrag: number }>>(`/reports/btw-betalingen?jaar=${jaar}`),
    monthlyCashflow: () => request<MonthlyCashflow[]>("/reports/monthly-cashflow"),
  },
  settings: {
    get: (key: string) => request<{ value: string }>(`/settings/${key}`),
    set: (key: string, value: string) =>
      request<{ value: string }>(`/settings/${key}`, { method: "PUT", body: JSON.stringify({ value }) }),
  },
  private: {
    transactions: (jaar: number, opts?: { maand?: number; onlyCosts?: boolean; rekening?: string }) => {
      const params = new URLSearchParams({ jaar: String(jaar) });
      if (opts?.maand) params.set("maand", String(opts.maand));
      if (opts?.onlyCosts) params.set("only_costs", "true");
      if (opts?.rekening) params.set("rekening", opts.rekening);
      return request<BankTransaction[]>(`/private/transactions?${params}`);
    },
    setCategorie: (txId: number, categorie: string, applyToNaam: boolean) =>
      request<{ updated: number }>(
        `/private/transactions/${txId}/categorie?categorie=${encodeURIComponent(categorie)}&apply_to_naam=${applyToNaam}`,
        { method: "POST" }
      ),
    setRecurring: (txId: number, isRecurring: boolean, applyToNaam: boolean) =>
      request<{ updated: number }>(
        `/private/transactions/${txId}/recurring?is_recurring=${isRecurring}&apply_to_naam=${applyToNaam}`,
        { method: "POST" }
      ),
    debts: {
      list: (onlyActief = false) =>
        request<Schuld[]>(`/private/debts${onlyActief ? "?only_actief=true" : ""}`),
      create: (data: Partial<Schuld>) =>
        request<Schuld>("/private/debts", { method: "POST", body: JSON.stringify(data) }),
      update: (id: number, data: Partial<Schuld>) =>
        request<Schuld>(`/private/debts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
      remove: (id: number) => request<void>(`/private/debts/${id}`, { method: "DELETE" }),
    },
  },
};
