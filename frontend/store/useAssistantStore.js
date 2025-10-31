import axios from "axios";
import { create } from "zustand";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  "http://localhost:8000";

const defaultMemoryItem = (text, id, tags = []) => ({
  id,
  text,
  tags,
  source: "user",
  added_at: new Date().toISOString(),
});

const generateId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `tmp-${Math.random().toString(16).slice(2)}`;
};

export const useAssistantStore = create((set, get) => ({
  sessionId: null,
  messages: [],
  memory: [],
  loading: false,
  memoryLoading: false,
  error: null,
  partialTranscript: "",
  ensureSession() {
    if (typeof window === "undefined") return null;
    let sessionId = get().sessionId;
    if (sessionId) return sessionId;

    sessionId = window.localStorage.getItem("tohum-session-id");
    if (!sessionId) {
      sessionId = generateId();
      window.localStorage.setItem("tohum-session-id", sessionId);
    }
    set({ sessionId });
    return sessionId;
  },
  async sendMessage(text, mode = "text") {
    const trimmed = text.trim();
    if (!trimmed) return;

    const sessionId = get().ensureSession();
    if (!sessionId) return;

    const userMessage = {
      id: generateId(),
      role: "user",
      text: trimmed,
    };
    set((state) => ({
      messages: [...state.messages, userMessage],
      loading: true,
      error: null,
    }));

    try {
      const { data } = await axios.post(`${API_BASE}/api/chat`, {
        session_id: sessionId,
        message: trimmed,
        mode,
      });

      const assistantMessage = {
        id: data.message_id,
        role: "assistant",
        text: data.reply,
        context: data.context ?? [],
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        memory: data.context && data.context.length
          ? data.context
          : state.memory,
        loading: false,
      }));
    } catch (error) {
      console.error("Chat request failed", error);
      set({
        loading: false,
        error:
          error?.response?.data?.detail ||
          error.message ||
          "Bilinmeyen bir hata oluştu.",
      });
    }
  },
  async remember(text, tags = []) {
    const trimmed = text.trim();
    if (!trimmed) return;
    const sessionId = get().ensureSession();
    if (!sessionId) return;

    try {
      const { data } = await axios.post(`${API_BASE}/api/memory/remember`, {
        text: trimmed,
        tags,
        session_id: sessionId,
      });
      set((state) => ({
        memory: [
          defaultMemoryItem(
            trimmed,
            data.memory_id,
            Array.isArray(tags) ? tags : []
          ),
          ...state.memory,
        ],
      }));
    } catch (error) {
      console.error("Remember failed", error);
      set({
        error:
          error?.response?.data?.detail ||
          error.message ||
          "Hafızaya kaydedilemedi.",
      });
    }
  },
  async refreshMemory() {
    const sessionId = get().ensureSession();
    if (!sessionId) return;

    set({ memoryLoading: true, error: null });
    try {
      const { data } = await axios.get(`${API_BASE}/api/memory/${sessionId}`);
      set((state) => ({
        memory: data.memory ?? state.memory,
        messages: data.messages ?? state.messages,
        memoryLoading: false,
      }));
    } catch (error) {
      console.error("Memory fetch failed", error);
      set({
        memoryLoading: false,
        error:
          error?.response?.data?.detail ||
          error.message ||
          "Hafıza verileri alınamadı.",
      });
    }
  },
  setPartialTranscript(text) {
    set({ partialTranscript: text });
  },
  resetPartial() {
    set({ partialTranscript: "" });
  },
  resetConversation() {
    set({
      messages: [],
      memory: [],
      error: null,
    });
  },
}));
