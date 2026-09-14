import { Fragment, useMemo, useState } from "react";
import type { PlanData } from "../api/types";
import { DataTable, TableEmpty } from "../components/DataTable";
import { ExpandButton } from "../components/ExpandableRow";
import { FilterChip } from "../components/FilterChipGroup";
import { tonnes } from "../lib";
import { usePlan } from "../state/PlanContext";
import { PageHeading, PanelHeader } from "./Overview";

const segments = ["A", "B", "C", "D"];

export function Production() {
  const { data } = usePlan();
  const [segment, setSegment] = useState("ALL");
  const [below, setBelow] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  if (!data) return null;

  const farms = useMemo(() => {
    const groups = data.farmSegmentBalances.reduce<
      Record<string, PlanData["farmSegmentBalances"]>
    >((all, row) => {
      (all[row.farmId] ??= []).push(row);
      return all;
    }, {});

    return Object.values(groups)
      .map((balances) => ({
        farmId: balances[0].farmId,
        balances,
        expected: balances.reduce((sum, row) => sum + row.expectedT, 0),
        actual: balances.reduce((sum, row) => sum + row.actualT, 0),
        local: balances.reduce((sum, row) => sum + row.localT, 0),
        variance: balances.reduce((sum, row) => sum + row.varianceT, 0),
      }))
      .filter(
        (farm) =>
          (segment === "ALL" ||
            farm.balances.some((row) => row.segment === segment)) &&
          (!below || farm.variance < 0),
      )
      .sort((a, b) => a.variance - b.variance);
  }, [data.farmSegmentBalances, segment, below]);

  const names = new Map(
    data.clientResults.map((client) => [client.clientId, client.name]),
  );

  return (
    <section className="space-y-5">
      <PageHeading
        title="Production"
        description="Segment performance and farm-level production balances."
      />
      <article className="overflow-hidden rounded-xl border border-atlas-line bg-white shadow-sm">
        <PanelHeader
          title="Farm production balances"
          subtitle={`${farms.length} farms shown`}
          action={
            <div
              className="flex max-w-full items-center justify-end gap-1 overflow-x-auto"
              aria-label="Filter farm balances"
            >
              <FilterChip
                active={segment === "ALL"}
                onClick={() => setSegment("ALL")}
              >
                All segments
              </FilterChip>
              {segments.map((item) => (
                <FilterChip
                  key={item}
                  active={segment === item}
                  onClick={() => setSegment(item)}
                >
                  {item}
                </FilterChip>
              ))}
              <span className="mx-1 h-5 w-px shrink-0 bg-atlas-line" />
              <FilterChip
                active={below}
                onClick={() => setBelow((value) => !value)}
              >
                Below plan only
              </FilterChip>
            </div>
          }
        />
        <DataTable
          headers={[
            { label: "Farm ID" },
            { label: "Expected", align: "right" },
            ...segments.map((item) => ({
              label: `Actual ${item}`,
              align: "right" as const,
            })),
            { label: "Total actual", align: "right" },
            { label: "Local", align: "right" },
            { label: "Details", align: "right" },
          ]}
        >
          {farms.length === 0 ? (
            <TableEmpty colSpan={9} title="No farms match these filters." />
          ) : (
            farms.map((farm) => {
              const expanded = open === farm.farmId;
              return (
                <Fragment key={farm.farmId}>
                  <tr
                    className={
                      expanded
                        ? "bg-atlas-sage/45 shadow-[inset_4px_0_#092328]"
                        : farm.variance < 0
                          ? "shadow-[inset_2px_0_#B94A48]"
                          : ""
                    }
                  >
                    <td>
                      <div className="flex items-center gap-2">
                        <i
                          className={`size-1.5 rounded-full ${farm.variance < 0 ? "bg-red-700" : "bg-atlas-green"}`}
                        />
                        <div>
                          <strong>{farm.farmId}</strong>
                          <span className="mt-1 block text-[10px] text-atlas-muted">
                            {farm.balances.length} segment records
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="text-right tabular-nums">
                      {tonnes(farm.expected)}
                    </td>
                    {segments.map((item) => {
                      const row = farm.balances.find(
                        (balance) => balance.segment === item,
                      );
                      return (
                        <td className="text-right" key={item}>
                          {row ? (
                            <>
                              <strong className="tabular-nums">
                                {tonnes(row.actualT)}
                              </strong>
                              {row.varianceT !== 0 && (
                                <span
                                  className={`ml-1 text-[10px] font-bold ${row.varianceT < 0 ? "text-atlas-primary" : "text-atlas-green"}`}
                                >
                                  {row.varianceT > 0 ? "+" : ""}
                                  {tonnes(row.varianceT)}
                                </span>
                              )}
                            </>
                          ) : (
                            <span className="text-atlas-muted">—</span>
                          )}
                        </td>
                      );
                    })}
                    <td className="text-right font-bold tabular-nums">
                      {tonnes(farm.actual)}
                    </td>
                    <td className="text-right tabular-nums">
                      {tonnes(farm.local)}
                    </td>
                    <td className="text-right">
                      <ExpandButton
                        open={expanded}
                        label={farm.farmId}
                        onClick={() => setOpen(expanded ? null : farm.farmId)}
                      />
                    </td>
                  </tr>

                  {expanded && (
                    <tr className="detail-row">
                      <td colSpan={9} className="bg-atlas-sage/30">
                        <div className="p-6">
                          <div className="mb-4 flex items-end justify-between">
                            <div>
                              <span className="text-[10px] font-extrabold uppercase tracking-widest text-atlas-primary">
                                Farm allocation overview
                              </span>
                              <strong className="mt-1 block text-lg">
                                {farm.farmId}
                              </strong>
                            </div>
                            <p className="text-xs text-atlas-muted">
                              {tonnes(farm.actual)} received across{" "}
                              {farm.balances.length} segments
                            </p>
                          </div>
                          <div className="grid gap-3 lg:grid-cols-2">
                            {farm.balances.map((balance) => {
                              const lines = data.allocations.filter(
                                (line) =>
                                  line.farmId === farm.farmId &&
                                  line.segment === balance.segment,
                              );
                              return (
                                <article
                                  className="overflow-hidden rounded-xl border border-atlas-sage border-l-4 border-l-atlas-primary bg-white shadow-sm"
                                  key={balance.segment}
                                >
                                  <header className="flex items-center gap-3 border-b border-atlas-line p-4">
                                    <span className="grid size-7 place-items-center rounded-md bg-atlas-primary text-xs font-bold text-white">
                                      {balance.segment}
                                    </span>
                                    <div>
                                      <strong>Segment {balance.segment}</strong>
                                      <small className="mt-1 block text-[10px] text-atlas-muted">
                                        {tonnes(balance.exportedT)} exported ·{" "}
                                        {tonnes(balance.localT)} local
                                      </small>
                                    </div>
                                  </header>
                                  <dl className="grid grid-cols-3 divide-x divide-atlas-line bg-atlas-sage/20">
                                    <Metric
                                      label="Expected"
                                      value={tonnes(balance.expectedT)}
                                    />
                                    <Metric
                                      label="Actual"
                                      value={tonnes(balance.actualT)}
                                    />
                                    <Metric
                                      label="Variance"
                                      value={`${balance.varianceT > 0 ? "+" : ""}${tonnes(balance.varianceT)}`}
                                      tone={
                                        balance.varianceT < 0
                                          ? "text-atlas-primary"
                                          : "text-atlas-green"
                                      }
                                    />
                                  </dl>
                                  <div className="p-4">
                                    <p className="mb-2 text-[10px] font-extrabold uppercase tracking-wider text-atlas-primary">
                                      Export allocation
                                    </p>
                                    {lines.length ? (
                                      lines.map((line) => (
                                        <div
                                          className="flex min-h-8 items-center justify-between border-t border-atlas-line text-xs"
                                          key={line.clientId}
                                        >
                                          <span>
                                            {names.get(line.clientId) ??
                                              line.clientId}
                                          </span>
                                          <strong>{tonnes(line.tonnes)}</strong>
                                        </div>
                                      ))
                                    ) : (
                                      <span className="text-xs text-atlas-muted">
                                        No export allocation
                                      </span>
                                    )}
                                  </div>
                                </article>
                              );
                            })}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })
          )}
        </DataTable>
      </article>
    </section>
  );
}

function Metric({
  label,
  value,
  tone = "",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="p-3">
      <dt className="text-[9px] font-extrabold uppercase tracking-wider text-atlas-muted">
        {label}
      </dt>
      <dd className={`mt-1 text-sm font-bold ${tone}`}>{value}</dd>
    </div>
  );
}
