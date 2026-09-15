import type { ReactNode } from "react";

export function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className={`inline-flex h-8 items-center gap-1 rounded-full border px-3 text-[11px] font-bold transition ${active ? "border-atlas-primary bg-white text-atlas-deep shadow-sm before:size-1.5 before:rounded-full before:bg-atlas-green" : "border-atlas-line bg-white/70 text-atlas-muted hover:border-atlas-primary hover:bg-white hover:text-atlas-deep"}`}
      onClick={onClick}
      aria-pressed={active}
    >
      {children}
    </button>
  );
}
