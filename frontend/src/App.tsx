import { Bot, RefreshCw } from "lucide-react";
import { useState } from "react";
import { AssistantDrawer } from "./assistant/AssistantDrawer";
import { ErrorBanner } from "./components/ErrorBanner";
import { LoadingSkeleton } from "./components/LoadingSkeleton";
import { usePlan } from "./state/PlanContext";
import { Commercial } from "./views/Commercial";
import { LocalResidual } from "./views/LocalResidual";
import { Overview } from "./views/Overview";
import { Production } from "./views/Production";

type Tab = "overview" | "production" | "commercial" | "local";

const tabs: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "production", label: "Production" },
  { id: "commercial", label: "Commercial" },
  { id: "local", label: "Local Residual" },
];

export default function App() {
  const { status, validationErrors, refetch } = usePlan();
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [recomputing, setRecomputing] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [commercialFilter, setCommercialFilter] = useState<string | undefined>(
    undefined,
  );

  async function recompute() {
    setRecomputing(true);
    await refetch();
    setRecomputing(false);
  }

  function handleTabClick(tab: Tab) {
    setActiveTab(tab);
    setCommercialFilter(undefined);
  }

  function handleNavigate(
    tab: "commercial" | "local" | "production",
    filter?: string,
  ) {
    setActiveTab(tab);
    if (tab === "commercial" && filter) {
      setCommercialFilter(filter);
    } else {
      setCommercialFilter(undefined);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_8%_-10%,#8BBB927A_0,transparent_31rem),linear-gradient(180deg,#DDEBE3_0%,#E6F0E9_42%,#F4F8F5_100%)]">
      <header className="border-b border-white/30 bg-linear-to-r from-atlas-deep via-atlas-primary to-atlas-green text-white">
        <div className="mx-auto flex h-22 w-[min(1464px,calc(100%-48px))] items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              className="size-11 rounded-xl object-cover shadow-sm"
              src="/logo/logo_icon.png"
              alt=""
            />
            <div>
              <small className="block text-[11px] font-extrabold uppercase tracking-widest text-atlas-sage">
                Atlas Fresh
              </small>
              <strong className="mt-0.5 block text-xl tracking-tight">
                Daily Export Planner
              </strong>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border border-white bg-white px-3 py-2 text-sm font-bold text-atlas-deep shadow-sm transition hover:bg-atlas-sage"
              onClick={() => setAssistantOpen(true)}
              aria-expanded={assistantOpen}
            >
              <Bot className="size-4" />
              Ask Atlas
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-atlas-sage px-3 py-2 text-sm font-bold text-atlas-deep shadow-sm hover:bg-white"
              onClick={() => void recompute()}
              disabled={recomputing}
            >
              <RefreshCw
                className={`size-4 ${recomputing ? "animate-spin" : ""}`}
              />
              {recomputing ? "Recomputing" : "Recompute"}
            </button>
          </div>
        </div>
      </header>

      <nav
        className="border-b border-atlas-line bg-[#DCEAE2]"
        aria-label="Plan views"
      >
        <div className="mx-auto flex h-13 w-[min(1464px,calc(100%-48px))] overflow-x-auto">
          {tabs.map((tab) => (
            <button
              type="button"
              key={tab.id}
              className={`relative px-5 text-[13px] font-bold ${activeTab === tab.id ? "bg-white text-atlas-primary after:absolute after:inset-x-0 after:bottom-0 after:h-0.75 after:bg-atlas-primary" : "text-atlas-muted hover:bg-white/70 hover:text-atlas-primary"}`}
              onClick={() => handleTabClick(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {status === "loading" && <LoadingSkeleton />}
      {status === "error" && <ErrorBanner onRetry={() => void refetch()} />}
      {status === "invalid" && (
        <ErrorBanner
          onRetry={() => void refetch()}
          detail={
            validationErrors
              .map((error) => `${error.sheet}: ${error.message}`)
              .join(" · ") || "The plan data did not pass validation."
          }
        />
      )}
      {status === "ready" && (
        <main className="mx-auto w-[min(1464px,calc(100%-48px))] py-8">
          {activeTab === "overview" && <Overview onNavigate={handleNavigate} />}
          {activeTab === "production" && <Production />}
          {activeTab === "commercial" && (
            <Commercial defaultFilter={commercialFilter} />
          )}
          {activeTab === "local" && <LocalResidual />}
        </main>
      )}
      <AssistantDrawer
        open={assistantOpen}
        onClose={() => setAssistantOpen(false)}
      />
    </div>
  );
}
