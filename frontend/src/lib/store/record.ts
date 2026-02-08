import { create } from "zustand";

const API = "/api";

// ─── Types ──────────────────────────────────────────

export interface RecordData {
  id: string;
  user_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  last_opened?: string | null;
  chat_model?: string | null;
  embed_model?: string | null;
  doc_count: number;
}

export interface DocumentInfo {
  id: string;
  record_id: string;
  filename: string;
  hash: string;
  created_at: string;
  chunk_count: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: RagSource[];
  model?: string | null;
  timestamp: string;
}

export interface RagSource {
  document_id: string;
  filename: string;
  chunk_id: string;
  snippet: string;
  score: number;
}

// ─── Store ──────────────────────────────────────────

interface RecordState {
  record: RecordData | null;
  documents: DocumentInfo[];
  messages: ChatMessage[];
  isLoading: boolean;
  isQuerying: boolean;
  isUploading: boolean;
  error: string | null;

  // Actions
  fetchRecord: (recordId: string) => Promise<void>;
  fetchDocuments: (recordId: string) => Promise<void>;
  fetchMessages: (recordId: string) => Promise<void>;
  uploadDocument: (recordId: string, file: File) => Promise<boolean>;
  sendQuery: (recordId: string, query: string) => Promise<void>;
  updateRecord: (recordId: string, data: { name?: string; description?: string; chat_model?: string; embed_model?: string }) => Promise<void>;
  saveMessages: (recordId: string) => Promise<void>;
  clearMessages: () => void;
  clearError: () => void;
  reset: () => void;
}

export const useRecordStore = create<RecordState>()((set, get) => ({
  record: null,
  documents: [],
  messages: [],
  isLoading: false,
  isQuerying: false,
  isUploading: false,
  error: null,

  fetchRecord: async (recordId: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API}/records/${recordId}`, {
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to load record" }));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data: RecordData = await res.json();
      set({ record: data, isLoading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Failed to load record", isLoading: false });
    }
  },

  fetchDocuments: async (recordId: string) => {
    try {
      const res = await fetch(`${API}/documents/list/${recordId}`, {
        credentials: "include",
      });
      if (!res.ok) return;
      const data = await res.json();
      set({ documents: data.documents || [] });
    } catch {
      // silent fail
    }
  },

  fetchMessages: async (recordId: string) => {
    try {
      const res = await fetch(`${API}/chat/${recordId}`, {
        credentials: "include",
      });
      if (!res.ok) return;
      const data = await res.json();
      set({ messages: data.messages || [] });
    } catch {
      // silent fail — start with empty chat
    }
  },

  uploadDocument: async (recordId: string, file: File) => {
    set({ isUploading: true, error: null });
    try {
      const formData = new FormData();
      formData.append("record_id", recordId);
      formData.append("file", file);

      const res = await fetch(`${API}/documents/upload`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || `Error ${res.status}`);
      }

      // Refresh documents list
      await get().fetchDocuments(recordId);
      set({ isUploading: false });
      return true;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Upload failed", isUploading: false });
      return false;
    }
  },

  sendQuery: async (recordId: string, query: string) => {
    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}_user`,
      role: "user",
      content: query,
      timestamp: new Date().toISOString(),
    };

    set((s) => ({ messages: [...s.messages, userMsg], isQuerying: true, error: null }));

    try {
      const res = await fetch(`${API}/rag/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ record_id: recordId, query, top_k: 5 }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Query failed" }));
        throw new Error(err.detail || `Error ${res.status}`);
      }

      const data = await res.json();
      const assistantMsg: ChatMessage = {
        id: `msg_${Date.now()}_ai`,
        role: "assistant",
        content: data.answer || "No answer available.",
        sources: data.sources || [],
        model: data.model,
        timestamp: new Date().toISOString(),
      };

      set((s) => ({ messages: [...s.messages, assistantMsg], isQuerying: false }));
      // Persist to backend
      void get().saveMessages(recordId);
    } catch (e) {
      const errMsg: ChatMessage = {
        id: `msg_${Date.now()}_err`,
        role: "assistant",
        content: `Error: ${e instanceof Error ? e.message : "Query failed"}`,
        timestamp: new Date().toISOString(),
      };
      set((s) => ({ messages: [...s.messages, errMsg], isQuerying: false }));
      // Persist error message too so user sees it on reload
      void get().saveMessages(recordId);
    }
  },

  updateRecord: async (recordId, data) => {
    try {
      const res = await fetch(`${API}/records/${recordId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(data),
      });
      if (!res.ok) return;
      const updated: RecordData = await res.json();
      set({ record: updated });
    } catch {
      // silent
    }
  },

  saveMessages: async (recordId: string) => {
    const { messages } = get();
    try {
      await fetch(`${API}/chat/${recordId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ record_id: recordId, messages }),
      });
    } catch {
      // silent — don't block UX for persistence failures
    }
  },

  clearMessages: () => set({ messages: [] }),
  clearError: () => set({ error: null }),
  reset: () =>
    set({
      record: null,
      documents: [],
      messages: [],
      isLoading: false,
      isQuerying: false,
      isUploading: false,
      error: null,
    }),
}));
