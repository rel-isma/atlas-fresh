import { ChevronDown } from "lucide-react";
export function ExpandButton({
  open,
  onClick,
  label,
}: {
  open: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className={`inline-flex h-8 min-w-19 items-center justify-between gap-1 rounded-md border px-2 text-[11px] font-bold transition ${open ? "border-atlas-primary bg-atlas-primary text-white shadow-sm" : "border-atlas-line bg-white text-atlas-deep hover:border-atlas-sage"}`}
      onClick={onClick}
      aria-expanded={open}
      aria-label={`${open ? "Hide" : "Show"} details for ${label}`}
    >
      {open ? "Hide" : "Details"}
      <ChevronDown
        className={`size-3 transition-transform ${open ? "rotate-180" : ""}`}
        aria-hidden="true"
      />
    </button>
  );
}
