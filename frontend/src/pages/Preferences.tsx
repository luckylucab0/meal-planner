// Preferences — Form für Vorlieben, Fitness-Ziele, Diät-Tags. End-to-End-Loop
// gegen `/api/preferences` (GET beim Mount, PUT beim Speichern).

import { useEffect, useState } from "react";
import {
  getPreferences,
  putPreferences,
  type FitnessGoal,
  type Preferences as PrefsT,
  type PreferencesUpdate,
} from "../lib/api";
import TagInput from "../components/TagInput";

const FITNESS_GOALS: { value: FitnessGoal; label: string }[] = [
  { value: "muskelaufbau", label: "Muskelaufbau" },
  { value: "abnehmen", label: "Abnehmen" },
  { value: "erhaltung", label: "Erhaltung" },
  { value: "ausdauer", label: "Ausdauer" },
];

const COMMON_DIET_TAGS = ["vegetarisch", "vegan", "low-carb", "high-protein", "glutenfrei", "laktosefrei"];

type Status = "idle" | "loading" | "saving" | "saved" | "error";

const emptyForm: PreferencesUpdate = {
  whitelist: [],
  blacklist: [],
  fitness_goal: "erhaltung",
  kcal_target: 2000,
  protein_target_g: 120,
  max_prep_min: 45,
  weekly_budget_chf: null,
  diet_tags: [],
};

export default function Preferences() {
  const [form, setForm] = useState<PreferencesUpdate>(emptyForm);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPreferences()
      .then((p: PrefsT) => {
        setForm({
          whitelist: p.whitelist,
          blacklist: p.blacklist,
          fitness_goal: p.fitness_goal,
          kcal_target: p.kcal_target,
          protein_target_g: p.protein_target_g,
          max_prep_min: p.max_prep_min,
          weekly_budget_chf: p.weekly_budget_chf,
          diet_tags: p.diet_tags,
        });
        setStatus("idle");
      })
      .catch((e) => {
        setError(String(e));
        setStatus("error");
      });
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("saving");
    setError(null);
    try {
      await putPreferences(form);
      setStatus("saved");
      setTimeout(() => setStatus("idle"), 1500);
    } catch (err) {
      setError(String(err));
      setStatus("error");
    }
  };

  const update = <K extends keyof PreferencesUpdate>(k: K, v: PreferencesUpdate[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  if (status === "loading") {
    return <p className="text-neutral-500">Lade…</p>;
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold">Vorlieben</h1>
      <p className="mt-2 text-sm text-neutral-500">
        Wird vom Agent bei jeder Plan-Generierung berücksichtigt.
      </p>

      <form onSubmit={save} className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Whitelist / Blacklist */}
        <div>
          <label className="mb-1 block text-sm font-medium">Lieblingszutaten</label>
          <TagInput
            value={form.whitelist}
            onChange={(v) => update("whitelist", v)}
            placeholder="z.B. Quinoa, Avocado…"
            ariaLabel="Lieblingszutaten"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Nicht erwünscht / Allergien</label>
          <TagInput
            value={form.blacklist}
            onChange={(v) => update("blacklist", v)}
            placeholder="z.B. Erdnüsse, Sellerie…"
            ariaLabel="Nicht erwünscht oder Allergien"
          />
        </div>

        {/* Fitness-Ziel */}
        <div>
          <label className="mb-1 block text-sm font-medium">Fitness-Ziel</label>
          <select
            value={form.fitness_goal}
            onChange={(e) => update("fitness_goal", e.target.value as FitnessGoal)}
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            {FITNESS_GOALS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* Kochzeit */}
        <div>
          <label className="mb-1 block text-sm font-medium">Max. Kochzeit pro Mahlzeit (Min)</label>
          <input
            type="number"
            min={5}
            max={240}
            step={5}
            value={form.max_prep_min}
            onChange={(e) => update("max_prep_min", Number(e.target.value))}
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>

        {/* Kalorien / Protein */}
        <div>
          <label className="mb-1 block text-sm font-medium">Kalorien-Ziel pro Tag (kcal)</label>
          <input
            type="number"
            min={800}
            max={6000}
            step={50}
            value={form.kcal_target}
            onChange={(e) => update("kcal_target", Number(e.target.value))}
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Protein-Ziel pro Tag (g)</label>
          <input
            type="number"
            min={20}
            max={400}
            step={5}
            value={form.protein_target_g}
            onChange={(e) => update("protein_target_g", Number(e.target.value))}
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>

        {/* Budget */}
        <div>
          <label className="mb-1 block text-sm font-medium">Budget pro Woche (CHF, optional)</label>
          <input
            type="number"
            min={0}
            max={10000}
            step={5}
            value={form.weekly_budget_chf ?? ""}
            onChange={(e) =>
              update("weekly_budget_chf", e.target.value === "" ? null : Number(e.target.value))
            }
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="leer = kein Limit"
          />
        </div>

        {/* Diet Tags */}
        <div className="md:col-span-2">
          <label className="mb-1 block text-sm font-medium">Diät-Tags</label>
          <TagInput
            value={form.diet_tags}
            onChange={(v) => update("diet_tags", v)}
            placeholder="vegetarisch, low-carb…"
            ariaLabel="Diät-Tags"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            {COMMON_DIET_TAGS.filter((t) => !form.diet_tags.includes(t)).map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => update("diet_tags", [...form.diet_tags, tag])}
                className="rounded-full border border-neutral-300 px-2 py-0.5 text-xs text-neutral-500 hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
              >
                + {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center gap-3 md:col-span-2">
          <button
            type="submit"
            disabled={status === "saving"}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-emerald-700 disabled:opacity-50"
          >
            {status === "saving" ? "Speichere…" : "Speichern"}
          </button>
          {status === "saved" && <span className="text-sm text-emerald-600">✓ gespeichert</span>}
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>
      </form>
    </section>
  );
}
