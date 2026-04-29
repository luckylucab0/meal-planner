// Schlanker Tag-Input — komma- oder enter-getrennte Eingabe, Klick auf Tag entfernt.

import { useState, type KeyboardEvent } from "react";

interface Props {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  ariaLabel?: string;
}

export default function TagInput({ value, onChange, placeholder, ariaLabel }: Props) {
  const [draft, setDraft] = useState("");

  const commit = () => {
    const trimmed = draft.trim();
    if (!trimmed) return;
    if (!value.includes(trimmed)) onChange([...value, trimmed]);
    setDraft("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit();
    } else if (e.key === "Backspace" && !draft && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-neutral-300 bg-white px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900">
      {value.map((tag) => (
        <button
          key={tag}
          type="button"
          onClick={() => onChange(value.filter((t) => t !== tag))}
          className="rounded-full bg-neutral-200 px-2 py-0.5 text-xs hover:bg-red-100 hover:line-through dark:bg-neutral-700 dark:hover:bg-red-900"
          aria-label={`${tag} entfernen`}
        >
          {tag} ×
        </button>
      ))}
      <input
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={commit}
        placeholder={placeholder}
        aria-label={ariaLabel}
        className="flex-1 min-w-[120px] bg-transparent text-sm outline-none"
      />
    </div>
  );
}
