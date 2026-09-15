import { ArrowRight, Bot, Send, Sparkles, X } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { askAssistant } from "../api/client";
import type { AssistantRequest, AssistantResponse } from "../api/types";

const suggested: Array<{ label: string; body: AssistantRequest }> = [
  {
    label: "Which clients are at risk?",
    body: { question: "at_risk_clients" },
  },
  { label: "Where are farm gaps?", body: { question: "farm_gaps" } },
  { label: "Explain local residual", body: { question: "local_residual" } },
];

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  citedIds?: string[];
  unavailable?: boolean;
};

export function AssistantDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const historyEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    historyEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [open, messages, busy]);

  async function submit(body: AssistantRequest, displayText: string) {
    if (busy) return;

    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", text: displayText },
    ]);
    setBusy(true);

    try {
      const response = await askAssistant(body);
      setMessages((current) => [...current, responseToMessage(response)]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          text: "The assistant is unavailable right now. Please try again in a moment.",
          unavailable: true,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function sendFreeText(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (!text) return;
    setQuestion("");
    void submit({ freeText: text }, text);
  }

  if (!open) return null;

  return createPortal(
    <aside
      className="fixed top-36 right-3 bottom-4 z-[9999] flex w-[30vw] min-w-96 max-w-125 flex-col overflow-hidden rounded-3xl border border-atlas-line bg-white shadow-2xl"
      aria-label="Atlas planning assistant"
    >
      <header className="flex h-17 shrink-0 items-center justify-between border-b border-atlas-line px-5">
        <div className="flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-xl bg-atlas-sage/25 text-atlas-primary">
            <Sparkles className="size-4" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-bold">Atlas assistant</h2>
            <p className="text-[11px] text-atlas-muted">
              Grounded in today’s plan
            </p>
          </div>
        </div>
        <button
          type="button"
          className="grid size-9 place-items-center rounded-full text-atlas-muted transition hover:bg-atlas-sage/15 hover:text-atlas-deep"
          onClick={onClose}
          aria-label="Close assistant"
        >
          <X className="size-5" />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col">
            <div className="flex flex-1 flex-col items-center justify-center pb-8 text-center">
              <span className="mb-5 grid size-14 place-items-center rounded-2xl bg-atlas-sage/20 text-atlas-primary">
                <Bot className="size-7" aria-hidden="true" />
              </span>
              <h3 className="max-w-60 text-2xl font-medium leading-tight text-atlas-primary">
                Explore today’s export plan
              </h3>
              <p className="mt-3 max-w-64 text-sm leading-6 text-atlas-muted">
                Get a quick explanation of risks, farm gaps, and local residual.
              </p>
            </div>

            <div className="grid gap-1 pb-2">
              {suggested.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className="group flex items-center gap-3 rounded-lg px-2 py-2.5 text-left text-xs font-semibold text-atlas-deep transition hover:bg-atlas-sage/15"
                  onClick={() => void submit(item.body, item.label)}
                  disabled={busy}
                >
                  <ArrowRight className="size-4 shrink-0 text-atlas-muted transition group-hover:translate-x-0.5 group-hover:text-atlas-primary" />
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-3 py-2">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    message.role === "user"
                      ? "max-w-[85%] rounded-br-md bg-atlas-primary text-white"
                      : message.unavailable
                        ? "max-w-[90%] rounded-bl-md border border-red-200 bg-red-200/40 text-atlas-deep"
                        : "max-w-[90%] rounded-bl-md bg-atlas-sage/15 text-atlas-deep"
                  }`}
                >
                  {message.role === "assistant" && (
                    <span className="mb-1.5 flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-wider text-atlas-primary">
                      <Sparkles className="size-3" />
                      Atlas
                    </span>
                  )}
                  {message.role === "user" && (
                    <span className="mb-1.5 block text-[10px] font-extrabold uppercase tracking-wider text-white/70">
                      You
                    </span>
                  )}
                  <p>{message.text}</p>
                  {message.citedIds && message.citedIds.length > 0 && (
                    <p className="mt-2 border-t border-atlas-line pt-2 text-[10px] text-atlas-muted">
                      Plan sources: {message.citedIds.join(", ")}
                    </p>
                  )}
                </div>
              </article>
            ))}
            {busy && (
              <div className="flex justify-start">
                <div className="inline-flex items-center gap-3 rounded-2xl rounded-bl-md bg-atlas-sage/15 px-4 py-3.5 text-sm text-atlas-muted">
                  <span className="flex items-center gap-1">
                    <span className="inline-block size-1.5 animate-bounce rounded-full bg-atlas-primary/60 [animation-delay:0ms]" />
                    <span className="inline-block size-1.5 animate-bounce rounded-full bg-atlas-primary/60 [animation-delay:150ms]" />
                    <span className="inline-block size-1.5 animate-bounce rounded-full bg-atlas-primary/60 [animation-delay:300ms]" />
                  </span>
                  Reviewing the plan…
                </div>
              </div>
            )}
            <div ref={historyEnd} />
          </div>
        )}
      </div>

      <form className="shrink-0 px-4 pb-4" onSubmit={sendFreeText}>
        <div className="rounded-2xl border border-atlas-line bg-white p-3 shadow-sm transition focus-within:border-atlas-primary focus-within:ring-2 focus-within:ring-atlas-sage/25">
          <label className="sr-only" htmlFor="assistant-question">
            Ask Atlas a question
          </label>
          <textarea
            id="assistant-question"
            className="min-h-16 w-full resize-none bg-transparent px-1 text-sm leading-6 outline-none placeholder:text-atlas-muted"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Ask about today’s plan"
            disabled={busy}
            maxLength={1000}
            rows={2}
          />
          <div className="mt-1 flex items-center justify-between">
            <span className="text-[10px] text-atlas-muted">Enter to send</span>
            <button
              type="submit"
              className="grid size-9 place-items-center rounded-full bg-atlas-primary text-white transition hover:bg-atlas-deep disabled:bg-atlas-line disabled:text-atlas-muted"
              disabled={!question.trim() || busy}
              aria-label="Send message"
            >
              <Send className="size-4" />
            </button>
          </div>
        </div>
        <p className="mt-2 text-center text-[10px] text-atlas-muted">
          Atlas can make mistakes. Review important decisions.
        </p>
      </form>
    </aside>,
    document.body,
  );
}

function responseToMessage(response: AssistantResponse): ChatMessage {
  if (response.available) {
    return {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      text: response.answer,
      citedIds: response.citedIds,
    };
  }

  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    text: response.fallbackAnswer ?? response.reason,
    unavailable: true,
  };
}
