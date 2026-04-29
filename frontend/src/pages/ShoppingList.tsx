// Einkaufsliste — gruppiert nach Kategorie, Checkbox-Status im LocalStorage,
// Print-Button, .txt-Download.

import { useEffect, useMemo, useState } from "react";
import {
  getCurrentPlan,
  getShoppingList,
  shoppingListTxtUrl,
  type ShoppingListResponse,
} from "../lib/api";
import { formatGerman } from "../lib/dates";

const STORAGE_PREFIX = "meal-planner.shopping-checked.";

function useChecked(planId: number | null) {
  const key = planId !== null ? STORAGE_PREFIX + planId : null;
  const [checked, setChecked] = useState<Set<number>>(() => {
    if (!key) return new Set();
    try {
      const raw = localStorage.getItem(key);
      return new Set(raw ? (JSON.parse(raw) as number[]) : []);
    } catch {
      return new Set();
    }
  });

  useEffect(() => {
    if (!key) return;
    localStorage.setItem(key, JSON.stringify([...checked]));
  }, [key, checked]);

  const toggle = (id: number) => {
    setChecked((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return { checked, toggle };
}

export default function ShoppingList() {
  const [planId, setPlanId] = useState<number | null>(null);
  const [data, setData] = useState<ShoppingListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { checked, toggle } = useChecked(planId);

  useEffect(() => {
    getCurrentPlan()
      .then((p) => {
        if (!p) {
          setLoading(false);
          return;
        }
        setPlanId(p.id);
        return getShoppingList(p.id);
      })
      .then((sl) => {
        if (sl) setData(sl);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });
  }, []);

  const totalEstimate = useMemo(() => {
    if (!data?.total_cost_chf) return null;
    return Number(data.total_cost_chf).toFixed(2);
  }, [data]);

  if (loading) return <p className="text-neutral-500">Lade…</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!data)
    return (
      <p className="rounded-md border border-dashed border-neutral-300 bg-neutral-50 p-8 text-center text-neutral-500 dark:border-neutral-700 dark:bg-neutral-900">
        Noch kein Plan vorhanden.
      </p>
    );

  return (
    <section className="print:!text-black">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-semibold">Einkaufsliste</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Woche ab {formatGerman(data.week_start)}
            {totalEstimate && ` · geschätzt CHF ${totalEstimate}`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={shoppingListTxtUrl(data.plan_id)}
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
          >
            ↓ .txt
          </a>
          <button
            onClick={() => window.print()}
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
          >
            Drucken
          </button>
        </div>
      </div>

      <h1 className="hidden text-xl font-semibold print:block">
        Einkaufsliste — Woche ab {formatGerman(data.week_start)}
      </h1>

      <div className="mt-6 space-y-6">
        {data.groups.map((group) => (
          <div key={group.category}>
            <h2 className="mb-2 border-b border-neutral-200 pb-1 text-sm font-semibold uppercase tracking-wide text-neutral-500 dark:border-neutral-700">
              {group.label}
            </h2>
            <ul className="space-y-1">
              {group.items.map((it) => (
                <li
                  key={it.product_id}
                  className="flex items-center gap-3 rounded px-1 py-1 hover:bg-neutral-50 dark:hover:bg-neutral-900"
                >
                  <input
                    type="checkbox"
                    checked={checked.has(it.product_id)}
                    onChange={() => toggle(it.product_id)}
                    className="h-4 w-4 cursor-pointer"
                    aria-label={it.name}
                  />
                  <span
                    className={
                      checked.has(it.product_id)
                        ? "flex-1 line-through text-neutral-400"
                        : "flex-1"
                    }
                  >
                    <span className="tabular-nums text-neutral-500">
                      {Math.round(it.grams_to_buy)} g
                    </span>{" "}
                    {it.name}
                    {it.packs !== null && it.pack_size_g !== null && (
                      <span className="ml-2 text-xs text-neutral-400">
                        ({it.packs}× {it.pack_size_g} g)
                      </span>
                    )}
                  </span>
                  {it.est_cost_chf !== null && (
                    <span className="text-xs tabular-nums text-neutral-500">
                      CHF {Number(it.est_cost_chf).toFixed(2)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
