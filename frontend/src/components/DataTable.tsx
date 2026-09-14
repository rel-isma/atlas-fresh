import type { ReactNode } from "react";
export type TableHeader = { label: string; align?: "left" | "right" };
export function DataTable({
  headers,
  children,
  className = "",
}: {
  headers: TableHeader[];
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`max-h-[65vh] overflow-auto ${className}`}>
      <table className="w-full min-w-max border-separate border-spacing-0 text-[12px]">
        <thead className="sticky top-0 z-10 bg-[#DCEAE2] shadow-[0_1px_0_#C5D9CE]">
          <tr>
            {headers.map((header) => (
              <th
                key={header.label}
                className={`h-10 px-4 text-[10px] font-extrabold uppercase tracking-wider text-atlas-muted ${header.align === "right" ? "text-right" : "text-left"}`}
              >
                {header.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_tr:not(.detail-row):hover]:bg-atlas-sage/25 [&_td]:h-14 [&_td]:border-t [&_td]:border-atlas-line [&_td]:px-4 [&_td]:align-middle [&_.detail-row>td]:h-auto [&_.detail-row>td]:p-0">
          {children}
        </tbody>
      </table>
    </div>
  );
}
export function TableEmpty({
  colSpan,
  title,
}: {
  colSpan: number;
  title: string;
}) {
  return (
    <tr>
      <td colSpan={colSpan} className="py-8 text-center text-atlas-muted">
        {title}
      </td>
    </tr>
  );
}
