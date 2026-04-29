// Modal zum Anstossen einer neuen Plan-Generierung. User wählt für jede
// Tag/Slot-Kombination an, ob er zuhause kocht; das Backend bekommt nur
// die markierten Slots.

import { useMemo, useState } from "react";
import Modal from "./Modal";
import { addDays, mondayOf, toISODate, WEEKDAYS } from "../lib/dates";
import { generatePlan, type PlanRead, type Slot } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  onGenerated: (plan: PlanRead) => void;
}

const SLOTS: Slot[] = ["lunch", "dinner"];

export default function GeneratePlanModal({ open, onClose, onGenerated }: Props) {
  const defaultMonday = useMemo(() => toISODate(mondayOf(new Date())), []);
  const [weekStart, setWeekStart] = useState(defaultMonday);
  const [notes, setNotes] = useState("");
  const [selected, setSelected] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (let i = 0; i < 7; i++) {
      const d = addDays(mondayOf(new Date()), i);
      const iso = toISODate(d);
      for (const slot of SLOTS) init[`${iso}|${slot}`] = true;
    }
    return init;
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const days = useMemo(() => {
    const monday = new Date(weekStart);
    return Array.from({ length: 7 }, (_, i) => toISODate(addDays(monday, i)));
  }, [weekStart]);

  const toggle = (date: string, slot: Slot) =>
    setSelected((s) => ({ ...s, [`${date}|${slot}`]: !s[`${date}|${slot}`] }));

  const submit = async () => {
    const slots = Object.entries(selected)
      .filter(([, v]) => v)
      .map(([k]) => {
        const [date, slot] = k.split("|");
        return { date, slot: slot as Slot };
      });
    if (slots.length === 0) {
      setError("Bitte mindestens eine Mahlzeit auswählen.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const plan = await generatePlan({
        week_start: weekStart,
        slots,
        notes: notes.trim() || undefined,
      });
      onGenerated(plan);
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Neuen Plan generieren" width="max-w-3xl">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium">Wochenstart (Montag)</label>
          <input
            type="date"
            value={weekStart}
            onChange={(e) => setWeekStart(e.target.value)}
            className="rounded-md border border-neutral-300 bg-white px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
        </div>

        <div>
          <p className="mb-2 text-sm font-medium">Wann bist du zuhause?</p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  <th className="py-1 pr-2"></th>
                  {days.map((d, i) => (
                    <th key={d} className="px-1 py-1 text-center font-medium">
                      <div>{WEEKDAYS[i]}</div>
                      <div className="text-xs text-neutral-500">{d.slice(5)}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {SLOTS.map((slot) => (
                  <tr key={slot}>
                    <td className="py-1 pr-2 text-right text-neutral-500">
                      {slot === "lunch" ? "Mittag" : "Abend"}
                    </td>
                    {days.map((d) => (
                      <td key={d + slot} className="px-1 py-1 text-center">
                        <input
                          type="checkbox"
                          checked={!!selected[`${d}|${slot}`]}
                          onChange={() => toggle(d, slot)}
                          className="h-4 w-4 cursor-pointer"
                          aria-label={`${d} ${slot}`}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Notizen (optional)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="z.B. Freitag kommen Gäste, eher festlich…"
            className="w-full rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
          >
            Abbrechen
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting}
            className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {submitting ? "Generiere…" : "Generieren"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
