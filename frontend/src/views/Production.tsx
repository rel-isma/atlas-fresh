import { useMemo, useState } from "react";
import type { Segment } from "../api/types";
import { DataTable, TableEmpty } from "../components/DataTable";
import { ExpandableTableRow, ExpandButton } from "../components/ExpandableRow";
import { FilterChip } from "../components/FilterChipGroup";
import { tonnes } from "../lib";
import { usePlan } from "../state/PlanContext";
import { PageHeading, PanelHeader } from "./Overview";

const segments: Segment[] = ["A", "B", "C", "D"];

export function Production() {
  const { data } = usePlan();
  const [segment, setSegment] = useState("ALL");
  const [below, setBelow] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  if (!data) return null;

  const farms = useMemo(() => {
    return data.farmSummaries
      .map((farm) => ({
        ...farm,
        balances: data.farmSegmentBalances.filter(
          (balance) => balance.farmId === farm.farmId,
        ),
      }))
      .filter(
        (farm) =>
          (segment === "ALL" ||
            farm.balances.some((row) => row.segment === segment)) &&
          (!below || farm.belowPlan),
      );
  }, [data.farmSummaries, data.farmSegmentBalances, segment, below]);

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
                <ExpandableTableRow
                  key={farm.farmId}
                  open={expanded}
                  colSpan={9}
                  hasRiskAccent={farm.belowPlan}
                  details={() => (
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
                          {tonnes(farm.actualT)} received across{" "}
                          {farm.balances.length} segments
                        </p>
                      </div>
                      <DataTable
                        className="overflow-hidden rounded-lg border border-atlas-line bg-white shadow-sm"
                        headers={[
                          { label: "Segment" },
                          { label: "Expected", align: "right" },
                          { label: "Actual", align: "right" },
                          { label: "Variance", align: "right" },
                          { label: "Exported", align: "right" },
                          { label: "Local", align: "right" },
                          { label: "Export allocation" },
                        ]}
                      >
                        {farm.balances.map((balance) => {
                          const lines = data.allocations.filter(
                            (line) =>
                              line.farmId === farm.farmId &&
                              line.segment === balance.segment,
                          );
                          return (
                            <tr key={balance.segment}>
                              <td>
                                <div className="flex items-center gap-2">
                                  <span className="grid size-7 place-items-center rounded-md bg-atlas-primary text-xs font-bold text-white">
                                    {balance.segment}
                                  </span>
                                  <strong>Segment {balance.segment}</strong>
                                </div>
                              </td>
                              <td className="text-right tabular-nums">
                                {tonnes(balance.expectedT)}
                              </td>
                              <td className="text-right font-bold tabular-nums">
                                {tonnes(balance.actualT)}
                              </td>
                              <td
                                className={`text-right font-bold tabular-nums ${balance.varianceDirection === "BELOW" ? "text-atlas-primary" : "text-atlas-green"}`}
                              >
                                {balance.varianceDirection === "ABOVE"
                                  ? "+"
                                  : ""}
                                {tonnes(balance.varianceT)}
                              </td>
                              <td className="text-right tabular-nums">
                                {tonnes(balance.exportedT)}
                              </td>
                              <td className="text-right tabular-nums">
                                {tonnes(balance.localT)}
                              </td>
                              <td className="min-w-60 whitespace-normal py-2">
                                {lines.length ? (
                                  <div className="grid gap-1.5">
                                    {lines.map((line) => (
                                      <div
                                        className="flex items-center justify-between gap-5 rounded bg-slate-100 px-2.5 py-1.5"
                                        key={line.clientId}
                                      >
                                        <span>
                                          {names.get(line.clientId) ??
                                            line.clientId}
                                        </span>
                                        <strong className="tabular-nums">
                                          {tonnes(line.tonnes)}
                                        </strong>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-xs text-atlas-muted">
                                    No export allocation
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </DataTable>
                    </div>
                  )}
                >
                  <td>
                    <div className="flex items-center gap-2">
                      <i
                        className={`size-1.5 rounded-full ${farm.belowPlan ? "bg-red-700" : "bg-atlas-green"}`}
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
                    {tonnes(farm.expectedT)}
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
                            {row.varianceDirection !== "ON_PLAN" && (
                              <span
                                className={`ml-1 text-[10px] font-bold ${row.varianceDirection === "BELOW" ? "text-atlas-primary" : "text-atlas-green"}`}
                              >
                                {row.varianceDirection === "ABOVE" ? "+" : ""}
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
                    {tonnes(farm.actualT)}
                  </td>
                  <td className="text-right tabular-nums">
                    {tonnes(farm.localT)}
                  </td>
                  <td className="text-right">
                    <ExpandButton
                      open={expanded}
                      label={farm.farmId}
                      onClick={() => setOpen(expanded ? null : farm.farmId)}
                    />
                  </td>
                </ExpandableTableRow>
              );
            })
          )}
        </DataTable>
      </article>
    </section>
  );
}
