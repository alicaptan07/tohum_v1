import Head from "next/head";
import { useEffect } from "react";

import { ChatBox } from "@/components/ChatBox";
import { MemoryPanel } from "@/components/MemoryPanel";
import { VoiceButton } from "@/components/VoiceButton";
import { useAssistantStore } from "@/store/useAssistantStore";

export default function HomePage() {
  const ensureSession = useAssistantStore((state) => state.ensureSession);
  const error = useAssistantStore((state) => state.error);

  useEffect(() => {
    ensureSession();
  }, [ensureSession]);

  return (
    <>
      <Head>
        <title>Tohum v1 Asistan</title>
      </Head>

      <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-4 py-10">
        <header className="space-y-3 text-center">
          <p className="text-sm uppercase tracking-[0.4em] text-emerald-400">
            TOHUM v1
          </p>
          <h1 className="text-3xl font-semibold text-slate-50 md:text-4xl">
            Kişisel Asistan Kontrol Paneli
          </h1>
          <p className="text-slate-400">
            Chat, sesli etkileşim ve hafıza yönetimini tek ekranda topla.
          </p>
        </header>

        {error && (
          <div className="mx-auto w-full max-w-3xl rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr,1fr]">
          <div className="flex flex-col gap-6">
            <ChatBox />
            <VoiceButton />
          </div>
          <MemoryPanel />
        </div>
      </div>
    </>
  );
}
