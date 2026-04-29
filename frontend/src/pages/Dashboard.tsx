// Dashboard — heutige Mahlzeiten, Makro-Donut und 7-Tage-Wochen-Chart.
// Quick-Action „Neuen Plan generieren" öffnet das gleiche Modal wie der
// Wochenplan-Header.

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getCurrentPlan,
  getMacrosRange,
  type MealRead,
  type PlanRead,
  type MacrosRange,
} from "../lib/api";
import { addDays, formatGerman, mondayOf, toISODate } from "../lib/dates";
import GeneratePlanModal from "../components/GeneratePlanModal";

const TODAY_ISO = toISODate(new Date());

export default function Dashboard() {
  const [plan, setPlan] = useState<PlanRead | null>(null);
  const [stats, setStats] = useState<MacrosRange | null>(null);
  const [genOpen, setGenOpen] = useState(false);

  const refresh = () => {
    Promise.all([getCurrentPlan(), getMacrosRange(weekStartISO(), weekEndISO())]).then(
      ([p, s]) => {
        setPlan(p);
        setStats(s);
      },
    );
  };

  useEffect(refresh, []);

  const todaysMeals = useMemo(
    () => (plan ? plan.meals.filter((m) => m.date === TODAY_ISO) : []),
    [plan],
  );

  const todaysMacros = useMemo(() => {
    return todaysMeals.reduce(
      (acc, m) => ({
        kcal: acc.kcal + m.macros.kcal,
        protein_g: acc.protein_g + m.macros.protein_g,
        carbs_g: acc.carbs_g + m.macros.carbs_g,
        fat_g: acc.fat_g + m.macros.fat_g,
      }),
      { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
    );
  }, [todaysMeals]);

  return (
    <section>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="mt-1 text-sm text-neutral-500">Heute: {formatGerman(TODAY_ISO)}</p>
        </div>
        <button
          onClick={() => setGenOpen(true)}
          className="rounded-md bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-700"
        >
          Neuen Plan generieren
        </button>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <TodayCard title="Heute" meals={todaysMeals} />
        <MacroDonut macros={todaysMacros} target={stats?.kcal_target ?? 2000} />
        <ProteinCard
          actual={todaysMacros.protein_g}
          target={stats?.protein_target_g ?? 120}
        />
      </div>

      <div className="mt-6 rounded-md border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900">
        <h2 className="mb-2 text-sm font-medium">7-Tage-Verlauf</h2>
        {stats && stats.days.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={stats.days.map((d) => ({ ...d, label: d.date.slice(5) }))}>
              <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
              <XAxis dataKey="label" fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="kcal" stroke="#10b981" name="kcal" dot={false} />
              <Line
                type="monotone"
                dataKey="protein_g"
                stroke="#0ea5e9"
                name="Protein g"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-neutral-500">Noch keine Daten.</p>
        )}
      </div>

      <div className="mt-6 rounded-md border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900">
        <h2 className="mb-2 text-sm font-medium">Soll vs. Ist (kcal)</h2>
        {stats && (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={stats.days.map((d) => ({ ...d, label: d.date.slice(5) }))}>
              <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
              <XAxis dataKey="label" fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Bar dataKey="kcal" fill="#10b981">
                {stats.days.map((d, i) => (
                  <Cell
                    key={i}
                    fill={
                      Math.abs(d.kcal - stats.kcal_target) / Math.max(stats.kcal_target, 1) <= 0.15
                        ? "#10b981"
                        : "#f59e0b"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <GeneratePlanModal
        open={genOpen}
        onClose={() => setGenOpen(false)}
        onGenerated={() => {
          refresh();
        }}
      />
    </section>
  );
}

function weekStartISO(): string {
  return toISODate(mondayOf(new Date()));
}
function weekEndISO(): string {
  return toISODate(addDays(mondayOf(new Date()), 6));
}

function TodayCard({ title, meals }: { title: string; meals: MealRead[] }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-700 dark:bg-neutral-900">
      <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
        {title}
      </h2>
      {meals.length === 0 ? (
        <p className="text-neutral-500">Heute keine Mahlzeiten geplant.</p>
      ) : (
        <ul className="space-y-2">
          {meals.map((m) => (
            <li key={m.id}>
              <div className="font-medium">
                {m.slot === "lunch" ? "Mittag" : "Abend"}: {m.title}
              </div>
              <div className="text-xs tabular-nums text-neutral-500">
                {Math.round(m.macros.kcal)} kcal · {Math.round(m.macros.protein_g)} g P
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MacroDonut({
  macros,
  target,
}: {
  macros: { kcal: number; protein_g: number; carbs_g: number; fat_g: number };
  target: number;
}) {
  const data = [
    { name: "Protein g", value: Math.max(macros.protein_g, 0) },
    { name: "Carbs g", value: Math.max(macros.carbs_g, 0) },
    { name: "Fett g", value: Math.max(macros.fat_g, 0) },
  ];
  const colors = ["#0ea5e9", "#10b981", "#f59e0b"];
  return (
    <div className="rounded-md border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-700 dark:bg-neutral-900">
      <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
        Makros heute
      </h2>
      <div className="text-center text-2xl font-semibold tabular-nums">
        {Math.round(macros.kcal)}
        <span className="text-sm font-normal text-neutral-500"> / {target} kcal</span>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={32} outerRadius={50}>
            {data.map((_, i) => (
              <Cell key={i} fill={colors[i]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function ProteinCard({ actual, target }: { actual: number; target: number }) {
  const pct = Math.min(100, Math.round((actual / target) * 100));
  return (
    <div className="rounded-md border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-700 dark:bg-neutral-900">
      <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
        Protein heute
      </h2>
      <div className="text-2xl font-semibold tabular-nums">
        {Math.round(actual)} g
        <span className="text-sm font-normal text-neutral-500"> / {target} g</span>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-700">
        <div
          className="h-full bg-sky-500 transition-all"
          style={{ width: `${pct}%` }}
          aria-label={`${pct}% des Protein-Ziels`}
        />
      </div>
      <div className="mt-1 text-xs text-neutral-500">{pct}% des Tagesziels</div>
    </div>
  );
}
