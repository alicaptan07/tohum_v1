import { useEffect, useRef, useState } from "react";

import { useAssistantStore } from "@/store/useAssistantStore";

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_BASE?.replace(/\/$/, "") ||
  "ws://localhost:8000";

export function VoiceButton() {
  const sendMessage = useAssistantStore((state) => state.sendMessage);
  const setPartial = useAssistantStore((state) => state.setPartialTranscript);
  const resetPartial = useAssistantStore((state) => state.resetPartial);

  const [status, setStatus] = useState("disconnected");
  const [error, setError] = useState(null);
  const [isRecording, setIsRecording] = useState(false);

  const wsRef = useRef(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      if (recorderRef.current && recorderRef.current.state !== "inactive") {
        recorderRef.current.stop();
      }
      cleanupStream();
    };
  }, []);

  const connect = () => {
    if (typeof window === "undefined") return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    try {
      setStatus("connecting");
      const ws = new WebSocket(`${WS_BASE}/ws/voice`);
      ws.binaryType = "arraybuffer";
      ws.onopen = () => {
        setStatus("ready");
        setError(null);
      };
      ws.onclose = () => {
        setStatus("disconnected");
        setIsRecording(false);
        cleanupStream();
      };
      ws.onerror = () => {
        setStatus("error");
        setError("WebSocket bağlantısı kurulamadı.");
      };
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "ready") {
            setStatus("ready");
            return;
          }
          if (payload.type === "partial") {
            setPartial(payload.text ?? "");
          } else if (payload.type === "final") {
            resetPartial();
            if (payload.text?.trim()) {
              sendMessage(payload.text.trim(), "voice");
            }
          } else if (payload.type === "reset") {
            resetPartial();
          } else if (payload.type === "error") {
            setError(payload.reason || "Ses işleme hatası");
          }
        } catch (parseError) {
          console.warn("Unexpected message from voice socket", parseError);
        }
      };
      wsRef.current = ws;
    } catch (connectionError) {
      console.error("WebSocket error", connectionError);
      setError("Ses servisi bağlanamadı.");
      setStatus("error");
    }
  };

  const cleanupStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const stopRecording = () => {
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
    cleanupStream();
    setIsRecording(false);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "flush" }));
    }
  };

  const startRecording = async () => {
    if (isRecording) {
      stopRecording();
      return;
    }

    connect();

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Tarayıcı mikrofon erişimini desteklemiyor.");
      return;
    }
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError("Ses kanalı hazır değil.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });
      recorderRef.current = recorder;
      resetPartial();

      recorder.ondataavailable = async (event) => {
        if (
          event.data.size > 0 &&
          wsRef.current &&
          wsRef.current.readyState === WebSocket.OPEN
        ) {
          const buffer = await event.data.arrayBuffer();
          wsRef.current.send(buffer);
        }
      };

      recorder.onstop = () => {
        cleanupStream();
      };

      recorder.start(250);
      setIsRecording(true);
      setStatus("recording");
    } catch (recordError) {
      console.error("Microphone access error", recordError);
      setError("Mikrofon erişimi reddedildi veya başarısız oldu.");
      setStatus("error");
    }
  };

  const buttonLabel = () => {
    if (isRecording) return "Kaydı durdur";
    if (status === "ready") return "Sesle konuş";
    if (status === "connecting") return "Bağlanıyor…";
    if (status === "error") return "Tekrar dene";
    return "Sesle konuş";
  };

  return (
    <div className="card flex flex-col gap-4 p-6">
      <header>
        <h2 className="text-lg font-semibold text-emerald-400">Sesli Etkileşim</h2>
        <p className="text-sm text-slate-400">
          Mikrofonla konuş, gerçek zamanlı transkript ve yanıt al.
        </p>
      </header>

      <button
        onClick={startRecording}
        className={`btn justify-center ${isRecording ? "bg-rose-500 hover:bg-rose-400 text-rose-50" : ""}`}
      >
        {buttonLabel()}
      </button>

      {error && (
        <p className="rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
          {error}
        </p>
      )}

      {isRecording && (
        <div className="flex items-center gap-3 text-sm text-emerald-300">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
          Dinleniyor…
          <button
            type="button"
            className="text-xs font-semibold text-slate-400 underline"
            onClick={stopRecording}
          >
            Durdur
          </button>
        </div>
      )}
    </div>
  );
}
