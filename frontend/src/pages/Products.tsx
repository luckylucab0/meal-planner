// Products — Browse/Suche der lokalen Zutaten-Bibliothek mit OFF-Lookup
// und manuellem Anlegen. Editieren bleibt für später (selten gebraucht).

import { useEffect, useState } from "react";
import {
  createProduct,
  deleteProduct,
  listProducts,
  lookupProduct,
  type Product,
  type ProductCreate,
} from "../lib/api";

const CATEGORIES = [
  "gemuese",
  "fruechte",
  "brot",
  "milchprodukte",
  "fleisch_fisch",
  "trockenwaren",
  "tiefkuehl",
  "getreide",
  "oele_gewuerze",
  "sonstiges",
];

const emptyForm: ProductCreate = {
  name: "",
  category: "sonstiges",
  default_unit: "g",
  kcal_per_100g: 0,
  protein_g: 0,
  carbs_g: 0,
  fat_g: 0,
  typical_pack_size_g: null,
  est_price_chf: null,
};

export default function Products() {
  const [items, setItems] = useState<Product[]>([]);
  const [query, setQuery] = useState("");
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<ProductCreate>(emptyForm);

  const refresh = (q = query) => {
    listProducts(q.trim() || undefined)
      .then(setItems)
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    refresh("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onLookup = async () => {
    if (!query.trim()) return;
    setInfo(null);
    setError(null);
    try {
      const res = await lookupProduct(query.trim());
      if (res.source_resolved === "not_found") {
        setInfo("Open Food Facts hat nichts gefunden — du kannst die Zutat manuell anlegen.");
      } else {
        setInfo(
          res.source_resolved === "off"
            ? `Aus Open Food Facts geladen: ${res.product?.name}`
            : `Bereits lokal vorhanden: ${res.product?.name}`,
        );
        refresh();
      }
    } catch (e) {
      setError(String(e));
    }
  };

  const onDelete = async (id: number) => {
    if (!confirm("Wirklich löschen?")) return;
    try {
      await deleteProduct(id);
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    try {
      await createProduct(form);
      setForm(emptyForm);
      setCreating(false);
      refresh();
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <section>
      <h1 className="text-2xl font-semibold">Zutaten-Bibliothek</h1>
      <p className="mt-2 text-sm text-neutral-500">
        Wird vom Agent als Lookup-Tabelle benutzt. Open Food Facts liefert Treffer auf Knopfdruck;
        eigene Zutaten kannst du jederzeit manuell anlegen.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && refresh()}
          placeholder="Suche…"
          className="flex-1 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
        <button
          onClick={() => refresh()}
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
        >
          Suchen
        </button>
        <button
          onClick={onLookup}
          disabled={!query.trim()}
          className="rounded-md bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-700 disabled:opacity-50"
        >
          via Open Food Facts
        </button>
        <button
          onClick={() => setCreating((v) => !v)}
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
        >
          {creating ? "Abbrechen" : "+ Manuell"}
        </button>
      </div>

      {info && <p className="mt-3 text-sm text-emerald-600">{info}</p>}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {creating && (
        <form
          onSubmit={onCreate}
          className="mt-4 grid grid-cols-1 gap-3 rounded-md border border-neutral-200 bg-neutral-50 p-4 md:grid-cols-3 dark:border-neutral-700 dark:bg-neutral-900"
        >
          <input
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Name (z.B. Pouletbrust)"
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            value={form.default_unit}
            onChange={(e) => setForm({ ...form, default_unit: e.target.value })}
            placeholder="Einheit (g)"
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
          <input
            required
            type="number"
            step={1}
            value={form.kcal_per_100g}
            onChange={(e) => setForm({ ...form, kcal_per_100g: Number(e.target.value) })}
            placeholder="kcal/100g"
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
          <input
            required
            type="number"
            step={0.1}
            value={form.protein_g}
            onChange={(e) => setForm({ ...form, protein_g: Number(e.target.value) })}
            placeholder="Protein g/100g"
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
          <input
            required
            type="number"
            step={0.1}
            value={form.carbs_g}
            onChange={(e) => setForm({ ...form, carbs_g: Number(e.target.value) })}
            placeholder="Carbs g/100g"
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
          <input
            required
            type="number"
            step={0.1}
            value={form.fat_g}
            onChange={(e) => setForm({ ...form, fat_g: Number(e.target.value) })}
            placeholder="Fett g/100g"
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
          <input
            type="number"
            step={1}
            value={form.typical_pack_size_g ?? ""}
            onChange={(e) =>
              setForm({
                ...form,
                typical_pack_size_g: e.target.value === "" ? null : Number(e.target.value),
              })
            }
            placeholder="typ. Pack-Grösse g"
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
          <input
            type="number"
            step={0.05}
            value={form.est_price_chf ?? ""}
            onChange={(e) =>
              setForm({
                ...form,
                est_price_chf: e.target.value === "" ? null : Number(e.target.value),
              })
            }
            placeholder="Preis CHF"
            className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
          />
          <div className="md:col-span-3">
            <button
              type="submit"
              className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-700"
            >
              Anlegen
            </button>
          </div>
        </form>
      )}

      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead className="text-left">
            <tr className="border-b border-neutral-200 dark:border-neutral-700">
              <th className="py-2 pr-3">Name</th>
              <th className="py-2 pr-3">Kategorie</th>
              <th className="py-2 pr-3">kcal/100g</th>
              <th className="py-2 pr-3">P/C/F</th>
              <th className="py-2 pr-3">Quelle</th>
              <th className="py-2 pr-3"></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-neutral-500">
                  Noch keine Zutaten. Such via Open Food Facts oder leg manuell an.
                </td>
              </tr>
            )}
            {items.map((p) => (
              <tr key={p.id} className="border-b border-neutral-100 dark:border-neutral-800">
                <td className="py-2 pr-3">{p.name}</td>
                <td className="py-2 pr-3 text-neutral-500">{p.category}</td>
                <td className="py-2 pr-3 tabular-nums">{p.kcal_per_100g}</td>
                <td className="py-2 pr-3 tabular-nums text-neutral-500">
                  {p.protein_g}/{p.carbs_g}/{p.fat_g}
                </td>
                <td className="py-2 pr-3">
                  <span
                    className={
                      "rounded px-2 py-0.5 text-xs " +
                      (p.source === "off"
                        ? "bg-sky-100 text-sky-800 dark:bg-sky-900 dark:text-sky-200"
                        : p.source === "manual"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
                          : "bg-neutral-200 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200")
                    }
                  >
                    {p.source}
                  </span>
                </td>
                <td className="py-2 pr-3">
                  <button
                    onClick={() => onDelete(p.id)}
                    className="text-xs text-red-600 hover:underline"
                  >
                    löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
