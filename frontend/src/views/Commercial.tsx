import { useState } from "react";
import type { ClientStatus } from "../api/types";
import { DataTable, TableEmpty } from "../components/DataTable";
import { ExpandableTableRow, ExpandButton } from "../components/ExpandableRow";
import { FilterChip } from "../components/FilterChipGroup";
import { StatusBadge } from "../components/StatusBadge";
import { eur, reasonLabel, tonnes } from "../lib";
import { usePlan } from "../state/PlanContext";
import { PageHeading, PanelHeader } from "./Overview";

type FilterValue = "ALL" | "AT_RISK" | ClientStatus;

export function Commercial({ defaultFilter }: { defaultFilter?: string }) {
  const { data } = usePlan();
  const [filter, setFilter] = useState<FilterValue>(
    defaultFilter === "risk" ? "AT_RISK" : "ALL",
  );
  const [open, setOpen] = useState<string | null>(null);
  if (!data) return null;

  const counts: Record<ClientStatus, number> = {
    COMPLETE: data.clientStatusSummary.completeCount,
    PARTIAL: data.clientStatusSummary.partialCount,
    UNSERVED: data.clientStatusSummary.unservedCount,
  };
  const clients = data.clientResults.filter((client) =>
    filter === "ALL"
      ? true
      : filter === "AT_RISK"
        ? client.status !== "COMPLETE"
        : client.status === filter,
  );

  return (
    <section className="space-y-5">
      <PageHeading
        title="Commercial"
        description="Client demand, allocation outcomes, and fulfillment exceptions."
      />
      <article className="overflow-hidden rounded-xl border border-atlas-line bg-white shadow-sm">
        <PanelHeader
          title="Client allocation results"
          subtitle={`${clients.length} of ${data.clientStatusSummary.clientCount} clients · sorted by price descending`}
          action={
            <div
              className="flex max-w-full items-center justify-end gap-1 overflow-x-auto"
              aria-label="Filter client status"
            >
              <FilterChip
                active={filter === "ALL"}
                onClick={() => setFilter("ALL")}
              >
                All ({data.clientStatusSummary.clientCount})
              </FilterChip>
              <FilterChip
                active={filter === "AT_RISK"}
                onClick={() => setFilter("AT_RISK")}
              >
                At-risk ({data.kpis.atRiskCount})
              </FilterChip>
              {(["COMPLETE", "PARTIAL", "UNSERVED"] as const).map((status) => (
                <FilterChip
                  key={status}
                  active={filter === status}
                  onClick={() => setFilter(status)}
                >
                  {status[0] + status.slice(1).toLowerCase()} ({counts[status]})
                </FilterChip>
              ))}
            </div>
          }
        />
        <DataTable
          headers={[
            { label: "Client" },
            { label: "Mode" },
            { label: "Segment" },
            { label: "Price", align: "right" },
            { label: "Demand", align: "right" },
            { label: "Allocated", align: "right" },
            { label: "Remaining", align: "right" },
            { label: "Status" },
            { label: "Reason" },
            { label: "Details", align: "right" },
          ]}
        >
          {clients.length === 0 ? (
            <TableEmpty colSpan={10} title="No clients match this status." />
          ) : (
            clients.map((client) => {
              const lines = data.allocations.filter(
                (line) => line.clientId === client.clientId,
              );
              const expanded = open === client.clientId;
              return (
                <ExpandableTableRow
                  key={client.clientId}
                  open={expanded}
                  colSpan={10}
                  hasRiskAccent={client.status !== "COMPLETE"}
                  details={() => (
                    <div className="p-6">
                      <p className="mb-3 text-[10px] font-extrabold uppercase tracking-wider text-atlas-primary">
                        Allocation lines
                      </p>
                      <DataTable
                        className="overflow-hidden rounded-lg border border-atlas-sage bg-white shadow-sm"
                        headers={[
                          { label: "Farm ID" },
                          { label: "Segment" },
                          { label: "Tonnes", align: "right" },
                          { label: "Revenue", align: "right" },
                        ]}
                      >
                        {lines.map((line) => (
                          <tr key={`${line.farmId}-${line.segment}`}>
                            <td>{line.farmId}</td>
                            <td>
                              <span className="grid size-6 place-items-center rounded-md bg-atlas-sage/25 text-xs font-bold">
                                {line.segment}
                              </span>
                            </td>
                            <td className="text-right">
                              {tonnes(line.tonnes)}
                            </td>
                            <td className="text-right font-bold">
                              {eur(line.revenueEur)}
                            </td>
                          </tr>
                        ))}
                        <tr className="bg-atlas-sage/35 font-bold">
                          <td colSpan={2}>Client total</td>
                          <td className="text-right">
                            {tonnes(client.allocatedT)}
                          </td>
                          <td className="text-right">
                            {eur(client.revenueEur)}
                          </td>
                        </tr>
                      </DataTable>
                    </div>
                  )}
                >
                  <td>
                    <strong>{client.name}</strong>
                    <span className="mt-1 block text-[10px] text-atlas-muted">
                      {client.clientId}
                    </span>
                  </td>
                  <td className="text-[10px] font-extrabold text-atlas-muted">
                    {client.mode}
                  </td>
                  <td>
                    <span className="grid size-6 place-items-center rounded-md border border-atlas-line bg-white/60 text-[11px] font-bold">
                      {client.requestedSegment}
                    </span>
                  </td>
                  <td className="text-right tabular-nums">
                    {eur(client.priceEur)}
                  </td>
                  <td className="text-right tabular-nums">
                    {tonnes(client.demandT)}
                  </td>
                  <td className="text-right tabular-nums">
                    {tonnes(client.allocatedT)}
                  </td>
                  <td className="text-right tabular-nums">
                    {tonnes(client.remainingT)}
                  </td>
                  <td>
                    <StatusBadge status={client.status} />
                  </td>
                  <td className="max-w-50 whitespace-normal text-atlas-muted">
                    {reasonLabel(client.reason)}
                  </td>
                  <td className="text-right">
                    <ExpandButton
                      open={expanded}
                      label={client.name}
                      onClick={() => setOpen(expanded ? null : client.clientId)}
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
