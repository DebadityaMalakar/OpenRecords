import { useCallback, useEffect, useRef, useState } from "react";
import { useRecordStore, type ChatMessage } from "@/lib/store/record";
import MarkdownViewer from "./MarkdownViewer";

interface Props {
  recordId: string;
}

type ModelInfo = {
  id: string;
  provider: string;
  name: string;
  context_length?: number | null;
  categories?: string[];
};

export default function ChatPanel({ recordId }: Props) {
  const { messages, isQuerying, sendQuery, clearMessages, record, updateRecord } = useRecordStore();
  const [input, setInput] = useState("");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const fetchModels = async () => {
      setModelsLoading(true);
      setModelsError(null);
      try {
        const res = await fetch("/api/models", { credentials: "include" });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Failed to load models" }));
          throw new Error(err.detail || `Error ${res.status}`);
        }
        const data = await res.json();
        const rawModels = Array.isArray(data.models) ? data.models : [];
        const filtered = rawModels.filter((model: ModelInfo) => {
          const categories = model.categories || [];
          if (categories.includes("embedding")) return false;
          if (model.id?.toLowerCase().includes("embed")) return false;
          return true;
        });
        setModels(filtered);
      } catch (e) {
        setModelsError(e instanceof Error ? e.message : "Failed to load models");
      } finally {
        setModelsLoading(false);
      }
    };

    void fetchModels();
  }, []);

  useEffect(() => {
    if (!modelMenuOpen) return;
    const onClick = (event: MouseEvent) => {
      if (!modelMenuRef.current) return;
      if (!modelMenuRef.current.contains(event.target as Node)) {
        setModelMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [modelMenuOpen]);

  const selectedModel = models.find((model) => model.id === record?.chat_model);

  const handleSend = useCallback(() => {
    const q = input.trim();
    if (!q || isQuerying) return;
    setInput("");
    void sendQuery(recordId, q);
  }, [input, isQuerying, recordId, sendQuery]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
    // Allow plain Enter for newlines
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider">Chat</h2>
          {record?.chat_model && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-bg-tertiary text-text-subtle border border-border">
              {record.chat_model}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative" ref={modelMenuRef}>
            <button
              type="button"
              onClick={() => setModelMenuOpen((prev) => !prev)}
              className="text-xs px-2.5 py-1 rounded-full border border-border bg-bg-tertiary text-text-subtle hover:text-text transition-colors"
            >
              {selectedModel ? selectedModel.name || selectedModel.id : "Model"}
            </button>

            {modelMenuOpen && (
              <div className="absolute right-0 mt-3 w-72 rounded-2xl border border-border bg-bg-secondary shadow-lg overflow-hidden z-40">
                <div className="px-4 py-3 text-xs uppercase tracking-wide text-text-subtle">
                  Chat Models
                </div>
                {modelsLoading && (
                  <div className="px-4 py-3 text-sm text-text-muted">Loading models...</div>
                )}
                {modelsError && (
                  <div className="px-4 py-3 text-sm text-red-300">{modelsError}</div>
                )}
                {!modelsLoading && !modelsError && (
                  <div className="max-h-80 overflow-y-auto">
                    {models.map((model) => (
                      <button
                        key={model.id}
                        type="button"
                        onClick={() => {
                          void updateRecord(recordId, { chat_model: model.id });
                          setModelMenuOpen(false);
                        }}
                        className={`w-full text-left px-4 py-3 text-sm transition-colors hover:bg-bg-tertiary ${
                          model.id === record?.chat_model ? "bg-bg-tertiary" : ""
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-text">
                            {model.name || model.id}
                          </span>
                          {model.id === record?.chat_model && (
                            <span className="text-[10px] text-text-muted">Active</span>
                          )}
                        </div>
                        <div className="text-[11px] text-text-subtle mt-1">
                          {model.provider} • ctx {model.context_length || "?"}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          {messages.length > 0 && (
            <button onClick={clearMessages} className="text-xs text-text-subtle hover:text-text transition-colors">
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg className="w-16 h-16 mb-4 text-text-subtle/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <h3 className="text-lg font-semibold text-text-muted mb-1">Ask this record...</h3>
            <p className="text-sm text-text-subtle max-w-sm">
              Query your uploaded documents using natural language. AI will search through your sources and provide answers with citations.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isQuerying && (
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 rounded-full bi-gradient shrink-0 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">AI</span>
            </div>
            <div className="bg-bg-tertiary rounded-xl px-4 py-3 text-sm">
              <div className="flex items-center gap-2 text-text-muted">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-soft animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-soft animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-soft animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                Searching sources...
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-border p-4">
        <div className="flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask this record..."
            rows={1}
            className="flex-1 resize-none px-4 py-3 rounded-xl bg-bg-tertiary border border-border text-sm text-text placeholder:text-text-subtle focus:outline-none focus:ring-2 focus:ring-purple-soft/50 focus:border-transparent"
            style={{ maxHeight: "120px" }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isQuerying}
            className="shrink-0 w-10 h-10 rounded-xl bi-gradient text-white flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19V5m0 0l-7 7m7-7l7 7" />
            </svg>
          </button>
        </div>
        <p className="text-[10px] text-text-subtle mt-2 text-right">Ctrl+Enter to send</p>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold ${
          isUser ? "bg-bg-tertiary border border-border text-text-muted" : "bi-gradient text-white"
        }`}
      >
        {isUser ? "You" : "AI"}
      </div>

      <div className={`max-w-[80%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-purple-soft/20 border border-purple-soft/30 text-text whitespace-pre-wrap"
              : "bg-bg-tertiary text-text"
          }`}
        >
          {isUser ? (
            message.content
          ) : (
            <MarkdownViewer content={message.content} />
          )}
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-[10px] text-text-subtle font-medium uppercase tracking-wider">Sources</p>
            {message.sources.map((src) => (
              <div
                key={src.chunk_id}
                className="text-xs px-3 py-2 rounded-lg bg-bg-tertiary/60 border border-border text-text-muted"
              >
                <span className="font-medium text-text">{src.filename}</span>
                <span className="text-text-subtle"> — {src.snippet.slice(0, 100)}...</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
