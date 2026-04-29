// Schlanker Modal-Wrapper — Klick auf Backdrop schliesst, Escape bald folgt.

import { useEffect, type ReactNode } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  width?: string;
}

export default function Modal({ open, onClose, children, title, width = "max-w-2xl" }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 px-4 py-12"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`w-full ${width} rounded-lg bg-white p-6 shadow-xl dark:bg-neutral-900`}
      >
        {title && (
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
              aria-label="Schliessen"
            >
              ✕
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
