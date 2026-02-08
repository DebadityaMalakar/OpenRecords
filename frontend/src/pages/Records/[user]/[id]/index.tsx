import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";

import { useAuthStore } from "@/lib/store/auth";
import { useRecordStore } from "@/lib/store/record";

import OnboardingWizard from "@/components/records/OnboardingWizard";
import SourcesPanel from "@/components/records/SourcesPanel";
import ChatPanel from "@/components/records/ChatPanel";
import ToolsPanel from "@/components/records/ToolsPanel";
import ThemeToggle from "@/components/ThemeToggle";

// ─── Panel resize constants ─────────────────────────
const MIN_PANEL = 200;
const DEFAULT_LEFT = 280;
const DEFAULT_RIGHT = 280;

export default function RecordWorkspace() {
  const router = useRouter();
  const { user } = useAuthStore();
  const store = useRecordStore();

  // Router params
  const { user: userParam, id: recordId } = router.query as {
    user?: string;
    id?: string;
  };
  const isNew = router.query.new === "True";

  // ─── State ──────────────────────────────────────
  const [onboarding, setOnboarding] = useState(isNew);
  const [leftWidth, setLeftWidth] = useState(DEFAULT_LEFT);
  const [rightWidth, setRightWidth] = useState(DEFAULT_RIGHT);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [resizing, setResizing] = useState<"left" | "right" | null>(null);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");

  const containerRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  // ─── Auth guard ─────────────────────────────────
  useEffect(() => {
    if (!router.isReady) return;
    const currentUser = useAuthStore.getState().user;
    if (!currentUser) {
      void router.push("/login");
      return;
    }
    // Validate ownership
    if (userParam && !userParam.includes(currentUser.id)) {
      void router.push("/Home");
    }
  }, [router.isReady, userParam, router]);

  // ─── Sync onboarding from query ─────────────────
  useEffect(() => {
    setOnboarding(isNew);
  }, [isNew]);

  // ─── Load record + docs ─────────────────────────
  useEffect(() => {
    if (!router.isReady || !recordId) return;
    void store.fetchRecord(recordId);
    void store.fetchDocuments(recordId);
    void store.fetchMessages(recordId);
    return () => store.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordId, router.isReady]);

  // ─── Keyboard shortcuts ─────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case "s":
            e.preventDefault();
            setLeftOpen((v) => !v);
            break;
          case "t":
            e.preventDefault();
            setRightOpen((v) => !v);
            break;
          case "u":
            e.preventDefault();
            // trigger upload
            break;
          case "1":
            e.preventDefault();
            setLeftOpen(true);
            break;
          case "2":
            e.preventDefault();
            // focus chat (handled by ChatPanel)
            break;
          case "3":
            e.preventDefault();
            setRightOpen(true);
            break;
        }
      }
      if (e.key === "Escape") {
        // close modals
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // ─── Resize handlers ───────────────────────────
  const startResize = useCallback(
    (side: "left" | "right") => (e: React.MouseEvent) => {
      e.preventDefault();
      setResizing(side);
    },
    []
  );

  useEffect(() => {
    if (!resizing) return;

    const onMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();

      if (resizing === "left") {
        const w = Math.max(MIN_PANEL, Math.min(e.clientX - rect.left, rect.width * 0.4));
        setLeftWidth(w);
      } else {
        const w = Math.max(MIN_PANEL, Math.min(rect.right - e.clientX, rect.width * 0.4));
        setRightWidth(w);
      }
    };

    const onUp = () => setResizing(null);

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
  }, [resizing]);

  // ─── Onboarding complete ────────────────────────
  const handleOnboardingComplete = useCallback(() => {
    setOnboarding(false);
    // Remove ?new=True from URL
    const { new: _, ...rest } = router.query;
    void router.replace({ pathname: router.pathname, query: rest }, undefined, { shallow: true });
  }, [router]);

  // ─── Rename handlers ───────────────────────────
  const startRename = useCallback(() => {
    setRenameValue(store.record?.name || "");
    setIsRenaming(true);
    setTimeout(() => renameInputRef.current?.select(), 0);
  }, [store.record?.name]);

  const commitRename = useCallback(async () => {
    const trimmed = renameValue.trim();
    if (!trimmed || trimmed === store.record?.name || !recordId) {
      setIsRenaming(false);
      return;
    }
    await store.updateRecord(recordId, { name: trimmed });
    setIsRenaming(false);
  }, [renameValue, store, recordId]);

  const cancelRename = useCallback(() => {
    setIsRenaming(false);
  }, []);

  // ─── Render ─────────────────────────────────────
  if (!router.isReady || !recordId) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 rounded-full bi-gradient animate-spin" />
      </div>
    );
  }

  if (onboarding) {
    return <OnboardingWizard recordId={recordId} onComplete={handleOnboardingComplete} />;
  }

  if (store.isLoading && !store.record) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 rounded-full bi-gradient animate-spin" />
      </div>
    );
  }

  if (store.error && !store.record) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="text-center">
          <p className="text-red-400 mb-4">{store.error}</p>
          <Link href="/Home" className="text-sm text-purple-soft underline">
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background text-text overflow-hidden">
      {/* Top bar */}
      <header className="shrink-0 flex items-center justify-between px-4 py-2 border-b border-border bg-bg-secondary/90 backdrop-blur-md z-30">
        <div className="flex items-center gap-3">
          <Link href="/Home" className="flex items-center gap-2 group">
            <div className="w-6 h-6 bi-gradient rounded-full" />
            <span className="text-sm font-semibold tracking-tight hidden sm:inline">OpenRecords</span>
          </Link>
          <span className="text-text-subtle text-xs">/</span>
          {isRenaming ? (
            <input
              ref={renameInputRef}
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onBlur={() => void commitRename()}
              onKeyDown={(e) => {
                if (e.key === "Enter") void commitRename();
                if (e.key === "Escape") cancelRename();
              }}
              className="text-sm font-medium bg-transparent border-b border-purple-soft/60 outline-none px-1 py-0.5 max-w-[200px] text-text"
              autoFocus
            />
          ) : (
            <button
              onClick={startRename}
              title="Click to rename"
              className="text-sm font-medium truncate max-w-[200px] hover:text-purple-soft transition-colors cursor-text px-1 py-0.5 rounded hover:bg-bg-tertiary/50"
            >
              {store.record?.name || "Untitled"}
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle compact />
          {/* Toggle sources */}
          <button
            onClick={() => setLeftOpen((v) => !v)}
            className={`p-1.5 rounded-md text-xs transition-colors ${leftOpen ? "bg-bg-tertiary text-text" : "text-text-subtle hover:text-text"}`}
            title="Toggle Sources (Ctrl+S)"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>

          {/* Toggle tools */}
          <button
            onClick={() => setRightOpen((v) => !v)}
            className={`p-1.5 rounded-md text-xs transition-colors ${rightOpen ? "bg-bg-tertiary text-text" : "text-text-subtle hover:text-text"}`}
            title="Toggle Tools (Ctrl+T)"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>

          {/* Doc count badge */}
          <span className="text-[10px] text-text-subtle px-2 py-0.5 rounded-full border border-border">
            {store.documents.length} docs
          </span>
        </div>
      </header>

      {/* Three-panel body */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden" style={{ cursor: resizing ? "col-resize" : undefined }}>
        {/* Left: Sources */}
        {leftOpen && (
          <>
            <div
              className="shrink-0 border-r border-border bg-bg-secondary overflow-hidden"
              style={{ width: leftWidth }}
            >
              <SourcesPanel recordId={recordId} onUploadClick={() => {}} />
            </div>
            <div
              onMouseDown={startResize("left")}
              className="shrink-0 w-1 cursor-col-resize hover:bg-purple-soft/30 active:bg-purple-soft/50 transition-colors"
            />
          </>
        )}

        {/* Center: Chat */}
        <div className="flex-1 min-w-0 bg-background">
          <ChatPanel recordId={recordId} />
        </div>

        {/* Right: Tools */}
        {rightOpen && (
          <>
            <div
              onMouseDown={startResize("right")}
              className="shrink-0 w-1 cursor-col-resize hover:bg-purple-soft/30 active:bg-purple-soft/50 transition-colors"
            />
            <div
              className="shrink-0 border-l border-border bg-bg-secondary overflow-hidden"
              style={{ width: rightWidth }}
            >
              <ToolsPanel recordId={recordId} />
            </div>
          </>
        )}
      </div>

      {/* Mobile bottom tabs (small screens) */}
      <div className="sm:hidden shrink-0 flex border-t border-border bg-bg-secondary">
        <button
          onClick={() => { setLeftOpen(true); setRightOpen(false); }}
          className={`flex-1 py-3 text-xs font-medium text-center ${leftOpen && !rightOpen ? "text-purple-soft" : "text-text-subtle"}`}
        >
          Sources
        </button>
        <button
          onClick={() => { setLeftOpen(false); setRightOpen(false); }}
          className={`flex-1 py-3 text-xs font-medium text-center ${!leftOpen && !rightOpen ? "text-purple-soft" : "text-text-subtle"}`}
        >
          Chat
        </button>
        <button
          onClick={() => { setLeftOpen(false); setRightOpen(true); }}
          className={`flex-1 py-3 text-xs font-medium text-center ${rightOpen && !leftOpen ? "text-purple-soft" : "text-text-subtle"}`}
        >
          Tools
        </button>
      </div>
    </div>
  );
}
