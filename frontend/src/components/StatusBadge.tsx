import { AlertTriangle, CheckCircle2, CircleX } from "lucide-react";
import type { ClientStatus } from "../api/types";
export function StatusBadge({ status }: { status: ClientStatus }) {
  const info =
    status === "COMPLETE"
      ? {
          label: "Complete",
          Icon: CheckCircle2,
          className: "bg-atlas-green text-white",
        }
      : status === "PARTIAL"
        ? {
            label: "Partial",
            Icon: AlertTriangle,
            className: "bg-red-700 text-white",
          }
        : {
            label: "Unserved",
            Icon: CircleX,
            className: "bg-atlas-deep text-white",
          };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-extrabold ${info.className}`}
    >
      <info.Icon className="size-3" aria-hidden="true" />
      {info.label}
    </span>
  );
}
