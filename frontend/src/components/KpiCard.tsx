import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
export function KpiCard({
  label,
  value,
  detail,
  tone = "neutral",
  onClick,
}: {
  label: string;
  value: ReactNode;
  detail: string;
  tone?: "neutral" | "green" | "amber" | "red";
  onClick?: () => void;
}) {
  const accent = {
    neutral: "bg-atlas-deep",
    green: "bg-atlas-green",
    amber: "bg-atlas-sage",
    red: "bg-red-700",
  }[tone];
  const Tag = onClick ? "button" : "article";
  return (
    <Tag
      className={`relative min-h-30 overflow-hidden rounded-xl border border-atlas-line bg-white px-5 py-4 text-left shadow-sm ${onClick ? "cursor-pointer transition-all duration-150 hover:-translate-y-0.5 hover:border-atlas-sage hover:shadow-md" : ""}`}
      {...(onClick ? { type: "button" as const, onClick } : {})}
    >
      <span className={`absolute inset-y-0 left-0 w-1 ${accent}`} />
      {onClick && (
        <span className="absolute right-4 top-4 grid size-7 place-items-center rounded-full border border-atlas-line bg-atlas-sage/20 text-atlas-primary">
          <ArrowUpRight className="size-4" aria-hidden="true" />
        </span>
      )}
      <p className="text-[10px] font-extrabold uppercase tracking-wider text-atlas-muted">
        {label}
      </p>
      <strong className="mt-2 block text-3xl leading-none tracking-tight text-atlas-deep">
        {value}
      </strong>
      <span className="mt-2 block text-xs text-atlas-muted">{detail}</span>
    </Tag>
  );
}
