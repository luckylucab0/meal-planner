// Typisierter Fetch-Wrapper. Wird im Verlauf der Implementierung pro Endpoint erweitert.

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(`API ${path} → ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ───── Preferences ─────────────────────────────────────────────────────────

export type FitnessGoal = "muskelaufbau" | "abnehmen" | "erhaltung" | "ausdauer";

export interface Preferences {
  whitelist: string[];
  blacklist: string[];
  fitness_goal: FitnessGoal;
  kcal_target: number;
  protein_target_g: number;
  max_prep_min: number;
  weekly_budget_chf: number | null;
  diet_tags: string[];
  updated_at: string;
}

export type PreferencesUpdate = Omit<Preferences, "updated_at">;

export const getPreferences = () => apiFetch<Preferences>("/api/preferences");

export const putPreferences = (payload: PreferencesUpdate) =>
  apiFetch<Preferences>("/api/preferences", {
    method: "PUT",
    body: JSON.stringify(payload),
  });

// ───── Products ────────────────────────────────────────────────────────────

export type ProductSource = "off" | "agent" | "manual";

export interface Product {
  id: number;
  name: string;
  name_normalized: string;
  category: string;
  default_unit: string;
  kcal_per_100g: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  typical_pack_size_g: number | null;
  est_price_chf: number | null;
  source: ProductSource;
  off_barcode: string | null;
  off_fetched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductCreate {
  name: string;
  category: string;
  default_unit: string;
  kcal_per_100g: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  typical_pack_size_g: number | null;
  est_price_chf: number | null;
}

export interface ProductLookupResult {
  source_resolved: "local" | "off" | "not_found";
  product: Product | null;
}

export const listProducts = (q?: string, category?: string, limit = 100) => {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  params.set("limit", String(limit));
  return apiFetch<Product[]>(`/api/products?${params.toString()}`);
};

export const createProduct = (payload: ProductCreate) =>
  apiFetch<Product>("/api/products", { method: "POST", body: JSON.stringify(payload) });

export const deleteProduct = (id: number) =>
  apiFetch<void>(`/api/products/${id}`, { method: "DELETE" });

export const lookupProduct = (name: string, force_remote = false) =>
  apiFetch<ProductLookupResult>("/api/products/lookup", {
    method: "POST",
    body: JSON.stringify({ name, force_remote }),
  });

// ───── Plans ───────────────────────────────────────────────────────────────

export type Slot = "lunch" | "dinner";

export interface IngredientRead {
  product_id: number;
  name: string;
  grams: number;
  category: string;
  est_price_chf: number | null;
}

export interface MealRead {
  id: number;
  date: string;
  slot: Slot;
  title: string;
  instructions: string;
  prep_time_min: number;
  macros: { kcal: number; protein_g: number; carbs_g: number; fat_g: number; incomplete: boolean };
  estimated_cost_chf: number | null;
  uses_leftovers_from_id: number | null;
  ingredients: IngredientRead[];
}

export interface PlanRead {
  id: number;
  week_start: string;
  generated_at: string;
  notes: string | null;
  weekly_totals: { avg_kcal?: number | null; avg_protein_g?: number | null; total_cost_chf?: number | null };
  meals: MealRead[];
}

export interface PlanSummary {
  id: number;
  week_start: string;
  generated_at: string;
  notes: string | null;
  weekly_totals: PlanRead["weekly_totals"];
  meals_count: number;
}

export interface SlotRequest {
  date: string;
  slot: Slot;
}

export interface PlanGenerateRequest {
  week_start: string;
  slots: SlotRequest[];
  notes?: string;
}

export const generatePlan = (payload: PlanGenerateRequest) =>
  apiFetch<PlanRead>("/api/plans/generate", { method: "POST", body: JSON.stringify(payload) });

export const getCurrentPlan = () => apiFetch<PlanRead | null>("/api/plans/current");

export const getPlan = (id: number) => apiFetch<PlanRead>(`/api/plans/${id}`);

export const listPlanHistory = (limit = 10) =>
  apiFetch<PlanSummary[]>(`/api/plans/history?limit=${limit}`);

export const deletePlan = (id: number) =>
  apiFetch<void>(`/api/plans/${id}`, { method: "DELETE" });

export const regenerateMeal = (planId: number, mealId: number) =>
  apiFetch<MealRead>(`/api/plans/${planId}/meals/${mealId}/regenerate`, { method: "POST" });

// ───── Shopping List ───────────────────────────────────────────────────────

export interface ShoppingItem {
  product_id: number;
  name: string;
  category: string;
  grams_needed: number;
  grams_to_buy: number;
  packs: number | null;
  pack_size_g: number | null;
  est_cost_chf: number | null;
}

export interface ShoppingGroup {
  category: string;
  label: string;
  items: ShoppingItem[];
}

export interface ShoppingListResponse {
  plan_id: number;
  week_start: string;
  groups: ShoppingGroup[];
  total_cost_chf: number | null;
}

export const getShoppingList = (planId: number) =>
  apiFetch<ShoppingListResponse>(`/api/shopping-list/${planId}`);

export const shoppingListTxtUrl = (planId: number) => `/api/shopping-list/${planId}.txt`;

// ───── Stats ───────────────────────────────────────────────────────────────

export interface DailyMacros {
  date: string;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  meals_count: number;
}

export interface MacrosRange {
  from: string;
  to: string;
  kcal_target: number;
  protein_target_g: number;
  days: DailyMacros[];
}

export const getMacrosRange = (from?: string, to?: string) => {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const qs = params.toString();
  return apiFetch<MacrosRange>(`/api/stats/macros${qs ? "?" + qs : ""}`);
};
