import { AlertCircle, RefreshCw } from "lucide-react";
export function ErrorBanner({
  onRetry,
  detail = "The export plan could not be loaded. Check that the API is running and try again.",
}: {
  onRetry: () => void;
  detail?: string;
}) {
  return (
    <main className="mx-auto w-[min(1464px,calc(100%-48px))] py-8">
      <div className="flex items-center gap-4 rounded-xl border border-red-200 bg-white p-6 text-red-800 shadow-sm">
        <AlertCircle className="size-6" aria-hidden="true" />
        <div className="flex-1">
          <h2 className="font-bold">Unable to load the plan</h2>
          <p className="mt-1 text-sm">{detail}</p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md bg-atlas-primary px-3 py-2 text-sm font-bold text-white"
          onClick={onRetry}
        >
          <RefreshCw className="size-4" aria-hidden="true" />
          Try again
        </button>
      </div>
    </main>
  );
}
