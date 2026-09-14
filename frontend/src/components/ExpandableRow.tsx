import { ChevronDown } from "lucide-react";
import type { ReactNode } from "react";

export function ExpandableTableRow({
  open,
  colSpan,
  hasRiskAccent = false,
  children,
  details,
}: {
  open: boolean;
  colSpan: number;
  hasRiskAccent?: boolean;
  children: ReactNode;
  details: () => ReactNode;
}) {
  return (
    <>
      <tr
        className={`${open ? "bg-slate-100" : ""} ${hasRiskAccent ? "shadow-[inset_2px_0_#B94A48]" : ""}`}
      >
        {children}
      </tr>
      {open && (
        <tr className="detail-row">
          <td colSpan={colSpan} className="bg-slate-50">
            {details()}
          </td>
        </tr>
      )}
    </>
  );
}

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
      className="inline-flex h-8 min-w-19 items-center justify-between gap-1 rounded-md border border-atlas-line bg-white px-2 text-[11px] font-bold text-atlas-deep transition hover:border-atlas-sage"
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
