// Detail-Modal pro Mahlzeit: Anleitung, Zutatenliste, Makros, Regenerate-Button.

import { useState } from "react";
import Modal from "./Modal";
import { regenerateMeal, type MealRead } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  planId: number;
  meal: MealRead | null;
  onUpdated: (meal: MealRead) => void;
}

export default function MealDetailModal({ open, onClose, planId, meal, onUpdated }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!meal) return null;

  const onRegenerate = async () => {
    setBusy(true);
    setError(null);
    try {
      const next = await regenerateMeal(planId, meal.id);
      onUpdated(next);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={meal.title} width="max-w-2xl">
      <div className="space-y-4 text-sm">
        <div className="flex flex-wrap gap-3 text-xs text-neutral-500">
          <span>{meal.date}</span>
          <span>{meal.slot === "lunch" ? "Mittag" : "Abend"}</span>
          <span>{meal.prep_time_min} min</span>
          {meal.estimated_cost_chf !== null && <span>~ CHF {Number(meal.estimated_cost_chf).toFixed(2)}</span>}
        </div>

        <div className="grid grid-cols-4 gap-2 rounded-md bg-neutral-100 p-3 dark:bg-neutral-800">
          <Macro label="kcal" value={meal.macros.kcal} />
          <Macro label="P" value={meal.macros.protein_g} unit="g" />
          <Macro label="C" value={meal.macros.carbs_g} unit="g" />
          <Macro label="F" value={meal.macros.fat_g} unit="g" />
        </div>

        <div>
          <h3 className="mb-1 font-medium">Zutaten</h3>
          <ul className="space-y-1">
            {meal.ingredients.map((i) => (
              <li key={i.product_id} className="flex justify-between border-b border-neutral-100 py-1 dark:border-neutral-800">
                <span>{i.name}</span>
                <span className="text-neutral-500">{i.grams} g</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="mb-1 font-medium">Anleitung</h3>
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
            {meal.instructions || "—"}
          </pre>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onRegenerate}
            disabled={busy}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
          >
            {busy ? "Generiere…" : "Mahlzeit ersetzen"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md bg-neutral-800 px-3 py-1.5 text-sm text-white hover:bg-neutral-900"
          >
            Schliessen
          </button>
        </div>
      </div>
    </Modal>
  );
}

function Macro({ label, value, unit }: { label: string; value: number; unit?: string }) {
  return (
    <div className="text-center">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className="font-semibold tabular-nums">
        {Math.round(value)}
        {unit ?? ""}
      </div>
    </div>
  );
}
