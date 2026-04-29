// Datumshilfen — wir arbeiten mit ISO-Strings (YYYY-MM-DD).

export const WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"] as const;

export function toISODate(d: Date): string {
  // Lokales Datum, ohne TZ-Umrechnung.
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function parseISODate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function mondayOf(d: Date): Date {
  const out = new Date(d);
  const dow = out.getDay(); // 0=Sun, 1=Mon, ...
  const offset = dow === 0 ? -6 : 1 - dow;
  out.setDate(out.getDate() + offset);
  return out;
}

export function addDays(d: Date, days: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() + days);
  return out;
}

export function formatGerman(iso: string): string {
  const d = parseISODate(iso);
  return d.toLocaleDateString("de-CH", { day: "2-digit", month: "2-digit" });
}
