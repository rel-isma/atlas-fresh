import { CheckCircle2, ShieldAlert } from "lucide-react";
import type { ValidationError } from "../api/types";
export function DataHealthBanner({
  invalid,
  errors = [],
}: {
  invalid?: boolean;
  errors?: ValidationError[];
}) {
  if (invalid)
    return (
      <div className="flex items-center gap-2 rounded-md border border-white/40 bg-white/10 px-3 py-2 text-xs text-white">
        <ShieldAlert className="size-4" aria-hidden="true" />
        <div>
          <strong>Data validation needs attention</strong>
          <p className="mt-0.5">
            {errors.length} issue{errors.length === 1 ? "" : "s"} found.
          </p>
        </div>
      </div>
    );
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/35 bg-white/10 px-3 py-2 text-xs font-bold text-white">
      <CheckCircle2 className="size-3.5" aria-hidden="true" />
      Data validated
    </span>
  );
}
