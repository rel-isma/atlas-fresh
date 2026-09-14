import type { ReactNode } from "react";
export function FilterChipGroup({
  children,
  label,
}: {
  children: ReactNode;
  label: string;
}) {
  return (
    <div
      className="flex min-h-13 items-center justify-end gap-1 overflow-x-auto border-b border-atlas-line bg-[#dceae2]/70 px-4"
      aria-label={label}
    >
      {children}
    </div>
  );
}
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
    >
      {children}
    </button>
  );
}
