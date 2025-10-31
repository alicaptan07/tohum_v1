import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

import { useAssistantStore } from "@/store/useAssistantStore";

export function ChatBox() {
  const ensureSession = useAssistantStore((state) => state.ensureSession);
  const messages = useAssistantStore((state) => state.messages);
  const loading = useAssistantStore((state) => state.loading);
  const sendMessage = useAssistantStore((state) => state.sendMessage);
  const partial = useAssistantStore((state) => state.partialTranscript);
  const [draft, setDraft] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    ensureSession();
  }, [ensureSession]);

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, partial]);

  const handleSubmit = (event) => {
    event.preventDefault();
    sendMessage(draft);
    setDraft("");
  };

  return (
    <section className="card flex h-full flex-col gap-6 p-6">
      <header>
        <h2 className="text-lg font-semibold text-emerald-400">Sohbet</h2>
        <p className="text-sm text-slate-400">
          Yazılı veya sesli mesajlarla etkileşime geç.
        </p>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-lg bg-slate-900/80 p-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {partial && (
          <div className="max-w-[75%] self-start rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-200">
            {partial}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-3">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Bir şeyler yaz…"
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-400/40"
        />
        <button type="submit" className="btn" disabled={loading || !draft.trim()}>
          Gönder
        </button>
      </form>
    </section>
  );
}

function MessageBubble({ message }) {
  const isAssistant = message.role === "assistant";
  return (
    <div
      className={clsx(
        "max-w-[80%] rounded-xl px-4 py-3 text-sm shadow-sm",
        isAssistant
          ? "self-start bg-slate-800/80 text-slate-100"
          : "self-end bg-emerald-500/80 text-emerald-950"
      )}
    >
      <p>{message.text}</p>
      {isAssistant && message.context && message.context.length > 0 && (
        <div className="mt-2 border-t border-slate-700 pt-2 text-xs text-slate-400">
          <p className="font-semibold text-emerald-300">Bağlam</p>
          <ul className="mt-1 list-inside list-disc space-y-1">
            {message.context.slice(0, 3).map((item) => (
              <li key={item.id}>{item.text}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
