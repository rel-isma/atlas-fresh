export function LoadingSkeleton() {
  return (
    <main className="mx-auto grid w-[min(1464px,calc(100%-48px))] gap-5 py-8">
      <div className="h-8 w-56 animate-pulse rounded bg-atlas-sage/30" />
      <div className="h-5 w-96 animate-pulse rounded bg-atlas-sage/30" />
      <div className="h-28 animate-pulse rounded-xl bg-atlas-sage/20" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <div
            className="h-30 animate-pulse rounded-xl bg-atlas-sage/20"
            key={index}
          />
        ))}
      </div>
      <div className="h-96 animate-pulse rounded-xl bg-atlas-sage/20" />
    </main>
  );
}
