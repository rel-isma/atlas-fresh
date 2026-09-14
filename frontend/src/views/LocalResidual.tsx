import { PackageOpen } from "lucide-react";
import { DataTable } from "../components/DataTable";
import { KpiCard } from "../components/KpiCard";
import { eur, tonnes } from "../lib";
import { usePlan } from "../state/PlanContext";
import { PageHeading, PanelHeader } from "./Overview";
export function LocalResidual() {
  const { data } = usePlan();
  if (!data) return null;
  const { kpis, localResidual } = data;
  return (
    <section className="space-y-5">
      <PageHeading
        title="Local residual"
        description="Volume redirected to the local market after export allocation."
      />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <KpiCard
          tone="amber"
          label="Local volume"
          value={tonnes(kpis.localVolumeT)}
          detail="Redirected from export"
        />
        <KpiCard
          label="Local value"
          value={eur(kpis.localValueEur)}
          detail="At local market price"
        />
      </div>
      <article className="flex gap-3 rounded-xl border border-atlas-sage border-l-4 border-l-atlas-green bg-white p-6 shadow-sm">
        <PackageOpen className="mt-0.5 size-5 shrink-0 text-atlas-green" />
        <p className="text-[15px] leading-6">{data.narrative.localResidual}</p>
      </article>
      {localResidual.length > 0 && (
        <div className="rounded-lg border border-atlas-sage bg-atlas-sage/15 px-4 py-3 text-sm">
          <strong>Estimated insight</strong>
          <span className="ml-2">
            Local value uses each residual row’s local market price.
          </span>
        </div>
      )}
      <article className="overflow-hidden rounded-xl border border-atlas-line bg-white shadow-sm">
        <PanelHeader
          title="Residual by farm"
          subtitle={`${localResidual.length} farm records`}
        />
        <DataTable
          headers={[
            { label: "Farm ID" },
            { label: "Segment" },
            { label: "Tonnes", align: "right" },
            { label: "Reference price", align: "right" },
            { label: "Local price", align: "right" },
            { label: "Local value", align: "right" },
          ]}
        >
          {localResidual.map((row) => (
            <tr key={`${row.farmId}-${row.segment}`}>
              <td className="font-bold">{row.farmId}</td>
              <td>
                <span className="grid size-6 place-items-center rounded-md border border-atlas-line bg-atlas-sage/15 text-xs font-bold">
                  {row.segment}
                </span>
              </td>
              <td className="text-right tabular-nums">{tonnes(row.tonnesT)}</td>
              <td className="text-right tabular-nums">
                {eur(row.referencePriceEur)}
              </td>
              <td className="text-right tabular-nums">
                {eur(row.localPriceEur)}
              </td>
              <td className="text-right font-bold tabular-nums">
                {eur(row.localValueEur)}
              </td>
            </tr>
          ))}
        </DataTable>
      </article>
    </section>
  );
}
