import type { CSSProperties, ReactNode } from "react";
import {
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
  type TooltipProps,
} from "recharts";
import type {
  NameType,
  ValueType,
} from "recharts/types/component/DefaultTooltipContent";

export type ChartConfig = Record<string, { label?: ReactNode; color?: string }>;

export function ChartContainer({
  config,
  className = "",
  children,
}: {
  config: ChartConfig;
  className?: string;
  children: ReactNode;
}) {
  const variables = Object.fromEntries(
    Object.entries(config).map(([key, value]) => [
      `--color-${key}`,
      value.color ?? "currentColor",
    ]),
  );
  return (
    <div
      className={`h-full w-full ${className}`}
      style={variables as CSSProperties}
      data-chart="atlas"
    >
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export function ChartTooltip(props: TooltipProps<ValueType, NameType>) {
  return <Tooltip {...props} />;
}

export function ChartTooltipContent({
  active,
  payload,
  label,
}: Partial<TooltipContentProps<ValueType, NameType>>) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-atlas-line bg-white px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-bold text-atlas-deep">Segment {label}</p>
      {payload.map((item) => (
        <div
          className="flex items-center justify-between gap-4"
          key={String(item.dataKey)}
        >
          <span className="text-atlas-muted">
            {String(item.name ?? item.dataKey)}
          </span>
          <strong>{item.value} t</strong>
        </div>
      ))}
    </div>
  );
}
