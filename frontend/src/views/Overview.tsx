import { CheckCircle2 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts";
import type { ReactNode } from "react";
import type { PlanData } from "../api/types";
import { DataTable, TableEmpty } from "../components/DataTable";
import { KpiCard } from "../components/KpiCard";
import { StatusBadge } from "../components/StatusBadge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";
import { eur, percent, reasonLabel, tonnes } from "../lib";
import { usePlan } from "../state/PlanContext";

export function Overview({
  onNavigate,
}: {
  onNavigate: (
    tab: "commercial" | "local" | "production",
    filter?: string,
  ) => void;
}) {
  const { data } = usePlan();
  if (!data) return null;

  const {
    kpis,
    clientStatusSummary,
    clientResults,
    localResidual,
    segmentVariances,
  } = data;
  const risk = clientResults.filter((client) => client.status !== "COMPLETE");
  const counts = [
    { status: "COMPLETE" as const, count: clientStatusSummary.completeCount },
    { status: "PARTIAL" as const, count: clientStatusSummary.partialCount },
    { status: "UNSERVED" as const, count: clientStatusSummary.unservedCount },
  ];
  const complete = clientStatusSummary.completePct;
  const partialEnd = clientStatusSummary.partialEndPct;

  return (
    <section className="space-y-5">
      <PageHeading
        title="Plan overview"
        description="Production intake, export fulfillment, and value at a glance."
      />

      <article className="rounded-xl border border-atlas-line border-l-4 border-l-atlas-primary bg-white p-6 shadow-sm">
        <p className="mb-2 text-[11px] font-extrabold uppercase tracking-widest text-atlas-primary">
          Summary of today's plan
        </p>
        <div className="flex gap-3 text-[15px] leading-6">
          <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-atlas-green" />
          <p>
            {data.narrative.overview} {data.narrative.localResidual}
          </p>
        </div>
      </article>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <KpiCard
          label="Actual received"
          value={tonnes(kpis.actualReceivedT)}
          detail={`vs ${tonnes(kpis.expectedPlanT)} planned`}
          onClick={() => onNavigate("production")}
        />
        <KpiCard
          tone="green"
          label="Export"
          value={tonnes(kpis.exportT)}
          detail={`${percent(kpis.exportRate)} of actual`}
          onClick={() => onNavigate("commercial")}
        />
        <KpiCard
          tone="amber"
          label="Local volume"
          value={tonnes(kpis.localVolumeT)}
          detail={eur(kpis.localValueEur)}
          onClick={() => onNavigate("local")}
        />
        <KpiCard
          tone="red"
          label="At-risk clients"
          value={kpis.atRiskCount}
          detail="Partial or unserved"
          onClick={() => onNavigate("commercial", "risk")}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.45fr_1fr]">
        <ExpectedActualChart rows={segmentVariances} />

        <article className="overflow-hidden rounded-xl border border-atlas-line bg-white shadow-sm">
          <PanelHeader
            title="Client status"
            subtitle={`${clientStatusSummary.clientCount} export clients`}
          />
          <div className="flex min-h-58 items-center justify-center gap-10">
            <div
              className="grid size-40 place-items-center rounded-full"
              style={{
                background: `conic-gradient(#2A835F 0 ${complete}%, #B94A48 ${complete}% ${partialEnd}%, #092328 ${partialEnd}% 100%)`,
              }}
            >
              <div className="grid size-27 place-content-center rounded-full bg-white text-center">
                <strong className="text-2xl">
                  {clientStatusSummary.clientCount}
                </strong>
                <span className="text-xs text-atlas-muted">clients</span>
              </div>
            </div>
            <div className="grid gap-3 text-xs">
              {counts.map((item) => (
                <div
                  className="grid grid-cols-[8px_75px_20px] items-center gap-2"
                  key={item.status}
                >
                  <i
                    className={`size-2 rounded-full ${item.status === "COMPLETE" ? "bg-atlas-green" : item.status === "PARTIAL" ? "bg-red-700" : "bg-atlas-deep"}`}
                  />
                  <span>
                    {item.status[0] + item.status.slice(1).toLowerCase()}
                  </span>
                  <strong className="text-right">{item.count}</strong>
                </div>
              ))}
            </div>
          </div>
        </article>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Preview
          title="At-risk clients"
          subtitle={`${kpis.atRiskCount} require attention`}
          onClick={() => onNavigate("commercial", "risk")}
        >
          <DataTable
            headers={[
              { label: "Client" },
              { label: "Segment" },
              { label: "Status" },
              { label: "Remaining", align: "right" },
            ]}
          >
            {risk.length === 0 ? (
              <TableEmpty colSpan={4} title="No at-risk clients" />
            ) : (
              risk.slice(0, 4).map((client) => (
                <tr key={client.clientId}>
                  <td>
                    <strong>{client.name}</strong>
                    <span className="mt-1 block text-[10px] text-atlas-muted">
                      {reasonLabel(client.reason)}
                    </span>
                  </td>
                  <td>
                    <span className="grid size-6 place-items-center rounded-md border border-atlas-line bg-atlas-sage/15 text-[11px] font-bold">
                      {client.requestedSegment}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={client.status} />
                  </td>
                  <td className="text-right font-bold tabular-nums">
                    {tonnes(client.remainingT)}
                  </td>
                </tr>
              ))
            )}
          </DataTable>
        </Preview>

        <Preview
          title="Local residual"
          subtitle={`${localResidual.length} farm records`}
          onClick={() => onNavigate("local")}
        >
          <DataTable
            headers={[
              { label: "Farm" },
              { label: "Segment" },
              { label: "Tonnes", align: "right" },
              { label: "Reference", align: "right" },
              { label: "Local value", align: "right" },
            ]}
          >
            {localResidual.length === 0 ? (
              <TableEmpty colSpan={5} title="No residual today" />
            ) : (
              localResidual.slice(0, 4).map((item) => (
                <tr key={`${item.farmId}-${item.segment}`}>
                  <td className="font-bold">{item.farmId}</td>
                  <td>
                    <span className="grid size-6 place-items-center rounded-md border border-atlas-line bg-atlas-sage/15 text-[11px] font-bold">
                      {item.segment}
                    </span>
                  </td>
                  <td className="text-right tabular-nums">
                    {tonnes(item.tonnesT)}
                  </td>
                  <td className="text-right tabular-nums">
                    {eur(item.referencePriceEur)}
                  </td>
                  <td className="text-right font-bold tabular-nums">
                    {eur(item.localValueEur)}
                  </td>
                </tr>
              ))
            )}
          </DataTable>
        </Preview>
      </div>
    </section>
  );
}

function ExpectedActualChart({ rows }: { rows: PlanData["segmentVariances"] }) {
  const chartConfig = {
    expected: { label: "Expected", color: "#8BBB92" },
    actual: { label: "Actual", color: "#12544F" },
  } satisfies ChartConfig;
  const chartData = rows.map((row) => ({
    segment: row.segment,
    expected: row.expectedT,
    actual: row.actualT,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Expected vs actual</CardTitle>
        <CardDescription>Tonnes by quality segment</CardDescription>
      </CardHeader>
      <CardContent className="px-3 pb-4 pt-5 sm:px-5">
        <div className="h-60">
          <ChartContainer config={chartConfig}>
            <BarChart
              accessibilityLayer
              data={chartData}
              margin={{ top: 20, right: 8, left: -16, bottom: 0 }}
            >
              <CartesianGrid
                vertical={false}
                stroke="#C5D9CE"
                strokeDasharray="3 5"
              />
              <XAxis
                dataKey="segment"
                tickLine={false}
                axisLine={false}
                tickMargin={10}
                tick={{ fill: "#47645E", fontSize: 12, fontWeight: 700 }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={42}
                tick={{ fill: "#47645E", fontSize: 10 }}
                tickFormatter={(value) => `${value}t`}
              />
              <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
              <Bar
                dataKey="expected"
                name="Expected"
                fill="var(--color-expected)"
                radius={[5, 5, 0, 0]}
                maxBarSize={32}
              >
                <LabelList
                  dataKey="expected"
                  position="top"
                  fontSize={10}
                  fontWeight={700}
                  fill="#47645E"
                  formatter={(v: any) => typeof v === "number" ? `${parseFloat(v.toFixed(1))}t` : `${v ?? ""}`}
                />
              </Bar>
              <Bar
                dataKey="actual"
                name="Actual"
                fill="var(--color-actual)"
                radius={[5, 5, 0, 0]}
                maxBarSize={32}
              >
                <LabelList
                  dataKey="actual"
                  position="top"
                  fontSize={10}
                  fontWeight={700}
                  fill="#12544F"
                  formatter={(v: any) => typeof v === "number" ? `${parseFloat(v.toFixed(1))}t` : `${v ?? ""}`}
                />
              </Bar>
            </BarChart>
          </ChartContainer>
        </div>
        <div className="flex items-center justify-center gap-5 pt-3">
          <div className="flex items-center gap-1.5">
            <span className="inline-block size-2.5 rounded-sm" style={{ background: "#8BBB92" }} />
            <span className="text-xs font-medium text-atlas-muted">Expected</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block size-2.5 rounded-sm" style={{ background: "#12544F" }} />
            <span className="text-xs font-medium text-atlas-muted">Actual</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function PageHeading({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <header>
      <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
      <p className="mt-1 text-[15px] text-atlas-muted">{description}</p>
    </header>
  );
}

export function PanelHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex min-h-17 items-center justify-between gap-4 border-b border-atlas-line px-5">
      <div>
        <h2 className="text-sm font-bold">{title}</h2>
        <p className="mt-1 text-[11px] text-atlas-muted">{subtitle}</p>
      </div>
      {action && <div className="min-w-0 shrink">{action}</div>}
    </header>
  );
}

function Preview({
  title,
  subtitle,
  onClick,
  children,
}: {
  title: string;
  subtitle: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <article className="overflow-hidden rounded-xl border border-atlas-line bg-white shadow-sm">
      <header className="flex min-h-17 items-center justify-between border-b border-atlas-line px-5">
        <div>
          <h2 className="text-sm font-bold">{title}</h2>
          <p className="mt-1 text-[11px] text-atlas-muted">{subtitle}</p>
        </div>
        <button
          className="text-xs font-bold text-atlas-primary"
          onClick={onClick}
        >
          View all
        </button>
      </header>
      {children}
    </article>
  );
}
