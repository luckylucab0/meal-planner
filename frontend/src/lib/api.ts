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
