// Wochenplan — 7-Tage-Grid × 2 Slots. Klick auf eine Zelle öffnet das
// Detail-Modal. Über "Neuen Plan generieren" startet der Agent-Loop.

import { useEffect, useState } from "react";
import { getCurrentPlan, type MealRead, type PlanRead } from "../lib/api";
import { addDays, formatGerman, parseISODate, toISODate, WEEKDAYS } from "../lib/dates";
import GeneratePlanModal from "../components/GeneratePlanModal";
import MealDetailModal from "../components/MealDetailModal";

export default function WeekPlan() {
  const [plan, setPlan] = useState<PlanRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [genOpen, setGenOpen] = useState(false);
  const [activeMeal, setActiveMeal] = useState<MealRead | null>(null);

  const refresh = () =>
    getCurrentPlan()
      .then((p) => {
        setPlan(p);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });

  useEffect(() => {
    refresh();
  }, []);

  if (loading) return <p className="text-neutral-500">Lade…</p>;

  return (
    <section>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Wochenplan</h1>
          {plan && (
            <p className="mt-1 text-sm text-neutral-500">
              Woche ab {formatGerman(plan.week_start)} ·{" "}
              {plan.weekly_totals?.avg_kcal ? `Ø ${Math.round(plan.weekly_totals.avg_kcal)} kcal/Tag` : "—"} ·{" "}
              {plan.weekly_totals?.avg_protein_g
                ? `Ø ${Math.round(plan.weekly_totals.avg_protein_g)} g Protein/Tag`
                : "—"}
            </p>
          )}
        </div>
        <button
          onClick={() => setGenOpen(true)}
          className="rounded-md bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-700"
        >
          Neuen Plan generieren
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {!plan && (
        <p className="mt-6 rounded-md border border-dashed border-neutral-300 bg-neutral-50 p-8 text-center text-neutral-500 dark:border-neutral-700 dark:bg-neutral-900">
          Noch kein Plan vorhanden. Klick oben rechts auf „Neuen Plan generieren".
        </p>
      )}

      {plan && <PlanGrid plan={plan} onMealClick={setActiveMeal} />}

      <GeneratePlanModal
        open={genOpen}
        onClose={() => setGenOpen(false)}
        onGenerated={(p) => {
          setPlan(p);
          refresh();
        }}
      />
      <MealDetailModal
        open={activeMeal !== null}
        onClose={() => setActiveMeal(null)}
        planId={plan?.id ?? 0}
        meal={activeMeal}
        onUpdated={(updated) => {
          setActiveMeal(updated);
          refresh();
        }}
      />
    </section>
  );
}

function PlanGrid({ plan, onMealClick }: { plan: PlanRead; onMealClick: (m: MealRead) => void }) {
  const start = parseISODate(plan.week_start);
  const days = Array.from({ length: 7 }, (_, i) => toISODate(addDays(start, i)));

  const mealAt = (date: string, slot: "lunch" | "dinner") =>
    plan.meals.find((m) => m.date === date && m.slot === slot) ?? null;

  return (
    <div className="mt-6 grid grid-cols-7 gap-2">
      {days.map((d, i) => (
        <div key={d} className="flex flex-col gap-2">
          <div className="text-center text-xs text-neutral-500">
            <div className="font-medium">{WEEKDAYS[i]}</div>
            <div>{d.slice(5)}</div>
          </div>
          <Cell label="Mittag" meal={mealAt(d, "lunch")} onClick={onMealClick} />
          <Cell label="Abend" meal={mealAt(d, "dinner")} onClick={onMealClick} />
        </div>
      ))}
    </div>
  );
}

function Cell({
  label,
  meal,
  onClick,
}: {
  label: string;
  meal: MealRead | null;
  onClick: (m: MealRead) => void;
}) {
  if (!meal) {
    return (
      <div className="rounded-md border border-dashed border-neutral-200 bg-neutral-50 p-3 text-center text-xs text-neutral-400 dark:border-neutral-800 dark:bg-neutral-900">
        <div className="font-medium uppercase tracking-wide">{label}</div>
        <div className="mt-2">—</div>
      </div>
    );
  }
  return (
    <button
      type="button"
      onClick={() => onClick(meal)}
      className="flex flex-col gap-1 rounded-md border border-neutral-200 bg-white p-3 text-left text-sm shadow-sm hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-900 dark:hover:bg-neutral-800"
    >
      <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="line-clamp-2 font-medium">{meal.title}</div>
      <div className="text-xs text-neutral-500 tabular-nums">
        {Math.round(meal.macros.kcal)} kcal · {Math.round(meal.macros.protein_g)} g P · {meal.prep_time_min} min
      </div>
    </button>
  );
}
