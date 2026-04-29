// Settings — CalDAV-Credentials für Apple iCloud (App-spezifisches Passwort).
// Klartext-Passwort verlässt den Server nie wieder; das Frontend zeigt
// `caldav_password_set` als „Passwort hinterlegt: ja/nein".

import { useEffect, useState } from "react";
import {
  getAppSettings,
  getCurrentPlan,
  putAppSettings,
  syncPlanToApple,
  type AppSettings,
} from "../lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [username, setUsername] = useState("");
  const [calendarName, setCalendarName] = useState("Meal Plan");
  const [password, setPassword] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [currentPlanId, setCurrentPlanId] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([getAppSettings(), getCurrentPlan()]).then(([s, p]) => {
      setSettings(s);
      setUsername(s.caldav_username ?? "");
      setCalendarName(s.caldav_calendar_name);
      setEnabled(s.caldav_enabled);
      if (p) setCurrentPlanId(p.id);
    });
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setInfo(null);
    setError(null);
    try {
      const next = await putAppSettings({
        caldav_enabled: enabled,
        caldav_username: username.trim() || null,
        caldav_calendar_name: calendarName.trim() || "Meal Plan",
        caldav_password: password.trim() || null,
      });
      setSettings(next);
      setPassword("");
      setInfo("Gespeichert.");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const sync = async () => {
    if (!currentPlanId) return;
    setBusy(true);
    setInfo(null);
    setError(null);
    try {
      const r = await syncPlanToApple(currentPlanId);
      setInfo(`Synchronisiert: ${r.created} neu, ${r.updated} aktualisiert.`);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h1 className="text-2xl font-semibold">Einstellungen</h1>
      <p className="mt-2 text-sm text-neutral-500">
        Wochenplan automatisch in den Apple Kalender übertragen — via CalDAV mit einem
        App-spezifischen Passwort.
      </p>

      <h2 className="mt-6 text-lg font-medium">Apple iCloud (CalDAV)</h2>
      <details className="mt-2 rounded-md border border-neutral-200 bg-neutral-50 p-3 text-sm dark:border-neutral-700 dark:bg-neutral-900">
        <summary className="cursor-pointer text-neutral-600">
          Wie erstelle ich ein App-spezifisches Passwort?
        </summary>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-neutral-600 dark:text-neutral-400">
          <li>
            Logge dich auf <a className="underline" href="https://account.apple.com">account.apple.com</a> ein.
          </li>
          <li>
            Im Bereich <em>Anmeldung &amp; Sicherheit</em> →{" "}
            <em>App-spezifische Passwörter</em> → „Generieren".
          </li>
          <li>Vergib einen Namen wie „Meal Planner" und kopiere das 16-stellige Passwort.</li>
          <li>
            Hier eintragen — es verlässt den Server nie wieder unverschlüsselt (Fernet,
            verschlüsselt in der Datenbank).
          </li>
        </ol>
      </details>

      <form onSubmit={save} className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="flex items-center gap-2 md:col-span-2">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4"
          />
          <span className="text-sm">CalDAV-Sync aktivieren</span>
        </label>

        <div>
          <label className="mb-1 block text-sm font-medium">Apple-ID (E-Mail)</label>
          <input
            type="email"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="vorname@icloud.com"
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Kalender-Name</label>
          <input
            type="text"
            value={calendarName}
            onChange={(e) => setCalendarName(e.target.value)}
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>

        <div className="md:col-span-2">
          <label className="mb-1 block text-sm font-medium">
            App-spezifisches Passwort {settings?.caldav_password_set && "(hinterlegt)"}
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={
              settings?.caldav_password_set
                ? "leer lassen, um das bestehende Passwort zu behalten"
                : "16-stelliges Passwort von appleid.apple.com"
            }
            className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 md:col-span-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            Speichern
          </button>
          <button
            type="button"
            onClick={sync}
            disabled={busy || !enabled || !settings?.caldav_password_set || !currentPlanId}
            title={!currentPlanId ? "Kein aktueller Plan zum Synchronisieren." : ""}
            className="rounded-md border border-neutral-300 px-4 py-2 text-sm hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
          >
            Aktuellen Plan jetzt syncen
          </button>
          {info && <span className="text-sm text-emerald-600">{info}</span>}
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>
      </form>
    </section>
  );
}
