// Historie — Liste aller vergangenen Wochenpläne mit Detail-Link und Löschen.
// "Erneut verwenden" ist im MVP eine Re-Generation mit denselben Slots
// — als Stretch-Goal später, MVP zeigt Liste + .ics-Download.

import { useEffect, useState } from "react";
import {
  deletePlan as deletePlanApi,
  listPlanHistory,
  planIcsUrl,
  type PlanSummary,
} from "../lib/api";
import { formatGerman } from "../lib/dates";

export default function History() {
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = () =>
    listPlanHistory(50)
      .then((p) => {
        setPlans(p);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });

  useEffect(() => {
    refresh();
  }, []);

  const onDelete = async (id: number) => {
    if (!confirm("Diesen Plan wirklich löschen?")) return;
    try {
      await deletePlanApi(id);
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  if (loading) return <p className="text-neutral-500">Lade…</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <section>
      <h1 className="text-2xl font-semibold">Historie</h1>
      <p className="mt-2 text-sm text-neutral-500">Alle bisher generierten Wochenpläne.</p>

      {plans.length === 0 ? (
        <p className="mt-6 rounded-md border border-dashed border-neutral-300 bg-neutral-50 p-8 text-center text-neutral-500 dark:border-neutral-700 dark:bg-neutral-900">
          Noch keine Pläne vorhanden.
        </p>
      ) : (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-left dark:border-neutral-700">
                <th className="py-2 pr-3">Woche ab</th>
                <th className="py-2 pr-3">Mahlzeiten</th>
                <th className="py-2 pr-3">Ø kcal/Tag</th>
                <th className="py-2 pr-3">Ø Protein/Tag</th>
                <th className="py-2 pr-3">Notizen</th>
                <th className="py-2 pr-3"></th>
              </tr>
            </thead>
            <tbody>
              {plans.map((p) => (
                <tr key={p.id} className="border-b border-neutral-100 dark:border-neutral-800">
                  <td className="py-2 pr-3">{formatGerman(p.week_start)}</td>
                  <td className="py-2 pr-3 tabular-nums">{p.meals_count}</td>
                  <td className="py-2 pr-3 tabular-nums text-neutral-500">
                    {p.weekly_totals?.avg_kcal
                      ? Math.round(Number(p.weekly_totals.avg_kcal))
                      : "—"}
                  </td>
                  <td className="py-2 pr-3 tabular-nums text-neutral-500">
                    {p.weekly_totals?.avg_protein_g
                      ? Math.round(Number(p.weekly_totals.avg_protein_g))
                      : "—"}
                  </td>
                  <td className="max-w-xs truncate py-2 pr-3 text-neutral-500">{p.notes ?? "—"}</td>
                  <td className="py-2 pr-3">
                    <div className="flex gap-2 text-xs">
                      <a
                        href={planIcsUrl(p.id)}
                        className="text-sky-600 hover:underline"
                      >
                        .ics
                      </a>
                      <button
                        onClick={() => onDelete(p.id)}
                        className="text-red-600 hover:underline"
                      >
                        löschen
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
