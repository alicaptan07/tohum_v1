import Head from "next/head";
import { useEffect } from "react";

import { useAssistantStore } from "@/store/useAssistantStore";

export default function DashboardPage() {
  const memory = useAssistantStore((state) => state.memory);
  const messages = useAssistantStore((state) => state.messages);
  const refreshMemory = useAssistantStore((state) => state.refreshMemory);
  const ensureSession = useAssistantStore((state) => state.ensureSession);
  const loading = useAssistantStore((state) => state.memoryLoading);

  useEffect(() => {
    ensureSession();
    refreshMemory();
  }, [ensureSession, refreshMemory]);

  return (
    <>
      <Head>
        <title>Tohum v1 Hafıza Paneli</title>
      </Head>
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-8 px-4 py-10">
        <header className="space-y-2">
          <h1 className="text-3xl font-semibold text-slate-50">
            Hafıza Analizi
          </h1>
          <p className="text-slate-400">
            Hafızaya kaydedilen notları ve oturum mesajlarını incele.
          </p>
        </header>

        <section className="card space-y-4 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-emerald-400">
              Hafıza Kayıtları
            </h2>
            <button
              type="button"
              onClick={refreshMemory}
              className="btn bg-slate-800 text-slate-200 hover:bg-slate-700"
            >
              Yenile
            </button>
          </div>
          {loading && <p className="text-sm text-slate-400">Yükleniyor…</p>}
          {!loading && memory.length === 0 && (
            <p className="text-sm text-slate-500">
              Gösterilecek kayıt bulunamadı.
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800 text-sm">
              <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-4 py-2 text-left">Metin</th>
                  <th className="px-4 py-2 text-left">Etiketler</th>
                  <th className="px-4 py-2 text-left">Kaynak</th>
                  <th className="px-4 py-2 text-left">Zaman</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900">
                {memory.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-900/60">
                    <td className="px-4 py-3 text-slate-100">{item.text}</td>
                    <td className="px-4 py-3 text-slate-300">
                      {item.tags?.length
                        ? item.tags.map((tag) => `#${tag}`).join(", ")
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {item.source ?? "user"}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {item.added_at
                        ? new Date(item.added_at).toLocaleString("tr-TR")
                        : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card space-y-4 p-6">
          <h2 className="text-lg font-semibold text-emerald-400">
            Oturum Mesajları
          </h2>
          <div className="space-y-3">
            {messages.length === 0 && (
              <p className="text-sm text-slate-500">
                Henüz sohbet geçmişi yok. Ana panelden sohbet başlat.
              </p>
            )}
            {messages.map((message) => (
              <article
                key={message.id}
                className="rounded-lg border border-slate-800 bg-slate-900/70 p-3"
              >
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="uppercase tracking-wide">
                    {message.role}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-100">{message.text}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
