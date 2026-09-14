export const tonnes = (value: number) =>
  `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(value)} t`;
export const eur = (value: number) =>
  new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
export const percent = (value: number | null) =>
  value === null ? "—" : `${(value * 100).toFixed(1)}%`;
export const reasonLabel = (value: string | null) =>
  value === "STATION_CAPACITY_REACHED"
    ? "Station capacity reached"
    : value === "INSUFFICIENT_COMPATIBLE_SEGMENT"
      ? "Insufficient compatible segment"
      : "—";
