import type { HTMLAttributes } from "react";

export function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <article
      className={`rounded-xl border border-atlas-line bg-white shadow-sm ${className}`}
      {...props}
    />
  );
}

export function CardHeader({
  className = "",
  ...props
}: HTMLAttributes<HTMLElement>) {
  return (
    <header
      className={`border-b border-atlas-line px-5 py-4 ${className}`}
      {...props}
    />
  );
}

export function CardTitle({
  className = "",
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={`text-sm font-bold ${className}`} {...props} />;
}

export function CardDescription({
  className = "",
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={`mt-1 text-[11px] text-atlas-muted ${className}`}
      {...props}
    />
  );
}

export function CardContent({
  className = "",
  ...props
}: HTMLAttributes<HTMLElement>) {
  return <div className={className} {...props} />;
}
