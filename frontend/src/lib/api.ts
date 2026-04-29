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
