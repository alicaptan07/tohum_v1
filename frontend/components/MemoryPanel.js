import { useState } from "react";

import { useAssistantStore } from "@/store/useAssistantStore";

export function MemoryPanel() {
  const memory = useAssistantStore((state) => state.memory);
  const refreshMemory = useAssistantStore((state) => state.refreshMemory);
  const remember = useAssistantStore((state) => state.remember);
  const loading = useAssistantStore((state) => state.memoryLoading);

  const [note, setNote] = useState("");
  const [tags, setTags] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    const parsedTags = tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    remember(note, parsedTags);
    setNote("");
    setTags("");
  };

  return (
    <section className="card flex h-full flex-col gap-4 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-emerald-400">
            Hafıza Paneli
          </h2>
          <p className="text-sm text-slate-400">
            Toplanan notlar ve vektör hafıza sonuçları.
          </p>
        </div>
        <button
          type="button"
          onClick={refreshMemory}
          className="btn bg-slate-800 text-slate-200 hover:bg-slate-700"
        >
          Yenile
        </button>
      </header>

      <form onSubmit={handleSubmit} className="grid gap-3">
        <textarea
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Hatırla: Bugün 14:00 toplantı"
          rows={3}
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-400/40"
        />
        <input
          value={tags}
          onChange={(event) => setTags(event.target.value)}
          placeholder="Etiketler (virgülle ayırın)"
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-400/40"
        />
        <button type="submit" className="btn justify-center">
          Hafızaya Kaydet
        </button>
      </form>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-lg bg-slate-900/80 p-4">
        {loading && <p className="text-sm text-slate-400">Yükleniyor…</p>}
        {!loading && memory.length === 0 && (
          <p className="text-sm text-slate-500">
            Henüz kayıtlı bir not yok. Yukarıdan yeni bir not ekleyebilirsin.
          </p>
        )}
        {memory.map((item) => (
          <article
            key={item.id}
            className="rounded-lg border border-slate-800 bg-slate-900/60 p-3"
          >
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{item.source ?? "user"}</span>
              <time suppressHydrationWarning>
                {item.added_at
                  ? new Date(item.added_at).toLocaleString("tr-TR")
                  : "-"}
              </time>
            </div>
            <p className="mt-2 text-sm text-slate-100">{item.text}</p>
            {item.tags && item.tags.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-2 text-xs text-emerald-300">
                {item.tags.map((tag) => (
                  <li
                    key={tag}
                    className="rounded-full border border-emerald-500/40 px-2 py-1"
                  >
                    #{tag}
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
