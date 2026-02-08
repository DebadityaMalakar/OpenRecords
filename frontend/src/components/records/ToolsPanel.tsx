import { useCallback, useState, useEffect } from "react";
import { useRecordStore } from "@/lib/store/record";
import MarkdownViewer from "./MarkdownViewer";

interface Props {
  recordId: string;
}

type ToolId = "summary" | "outline" | "insights" | "infographic" | "pdf" | "export";

interface Tool {
  id: ToolId;
  name: string;
  description: string;
  icon: string;
}

interface PreviousInfographic {
  image_id: string;
  created_at: string;
  depth: "standard" | "detailed";
  model: string;
}

interface PreviousPdf {
  pdf_id: string;
  created_at: string;
  page_count: number;
  model: string;
}

const TOOLS: Tool[] = [
  { id: "summary", name: "Summary Generator", icon: "📝", description: "Generate a comprehensive summary of all uploaded documents" },
  { id: "outline", name: "Outline Generator", icon: "🧩", description: "Create a structured outline from your sources" },
  { id: "insights", name: "Insight Generator", icon: "📊", description: "Extract key themes, contradictions, and questions" },
  { id: "infographic", name: "Infographic Generator", icon: "🎨", description: "Create a visual infographic from your research" },
  { id: "pdf", name: "PDF Generator", icon: "📄", description: "Generate a PDF from chunk-by-chunk visuals" },
  { id: "export", name: "Export Tool", icon: "📤", description: "Export summaries, chat history, or sources" },
];

export default function ToolsPanel({ recordId }: Props) {
  const { record, documents, messages } = useRecordStore();
  const [activeTool, setActiveTool] = useState<ToolId | null>(null);
  const [toolOutput, setToolOutput] = useState<string | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageId, setImageId] = useState<string | null>(null);
  const [pdfId, setPdfId] = useState<string | null>(null);
  const [toolMeta, setToolMeta] = useState<{ docCount?: number; chunkCount?: number; model?: string } | null>(null);
  const [pdfMeta, setPdfMeta] = useState<{ pageCount?: number; chunkCount?: number; model?: string } | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [copied, setCopied] = useState(false);

  // Infographic settings
  const [infographicDepth, setInfographicDepth] = useState<"standard" | "detailed">("standard");
  const [customPrompt, setCustomPrompt] = useState("");
  const [showCustomPrompt, setShowCustomPrompt] = useState(false);
  const [previousInfographics, setPreviousInfographics] = useState<PreviousInfographic[]>([]);
  const [showInfographicSettings, setShowInfographicSettings] = useState(false);
  const [previousPdfs, setPreviousPdfs] = useState<PreviousPdf[]>([]);
  const [showPdfSettings, setShowPdfSettings] = useState(false);

  const handleCopy = useCallback(() => {
    if (!toolOutput) return;
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(toolOutput).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      });
    } else {
      const ta = document.createElement("textarea");
      ta.value = toolOutput;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  }, [toolOutput]);

  const handleDownload = useCallback(() => {
    if (!toolOutput) return;
    const toolLabel = TOOLS.find((t) => t.id === activeTool)?.name || "output";
    const filename = `${record?.name || "record"}-${toolLabel.toLowerCase().replace(/\s+/g, "-")}.txt`;
    const blob = new Blob([toolOutput], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }, [toolOutput, activeTool, record?.name]);

  const handleDownloadImage = useCallback(() => {
    if (!imageUrl) return;
    // Handle base64 data URL
    const link = document.createElement("a");
    link.href = imageUrl;
    link.download = `${record?.name || "record"}-infographic.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [imageUrl, record?.name]);

  const handleDownloadPdf = useCallback(async (targetId?: string) => {
    const id = targetId || pdfId;
    if (!id) return;
    try {
      const res = await fetch(`/api/rag/pdf/${id}`, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to download PDF");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${record?.name || "record"}-export.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setToolOutput(`Error: ${e instanceof Error ? e.message : "Failed to download PDF"}`);
    }
  }, [pdfId, record?.name]);

  const loadPreviousInfographics = useCallback(async () => {
    try {
      const res = await fetch(`/api/rag/infographics/${recordId}`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setPreviousInfographics(data.infographics || []);
      }
    } catch (e) {
      console.error("Failed to load previous infographics:", e);
    }
  }, [recordId]);

  const loadPreviousPdfs = useCallback(async () => {
    try {
      const res = await fetch(`/api/rag/pdfs/${recordId}`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setPreviousPdfs(data.pdfs || []);
      }
    } catch (e) {
      console.error("Failed to load previous PDFs:", e);
    }
  }, [recordId]);

  const loadPreviousImage = async (imgId: string) => {
    setIsRunning(true);
    try {
      const res = await fetch(`/api/rag/infographic/${imgId}`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setImageUrl(data.image_url);
        setImageId(data.image_id);
        setToolMeta({ model: data.model });
        setShowInfographicSettings(false);
      }
    } catch (e) {
      console.error("Failed to load image:", e);
      setToolOutput("Error: Failed to load previous infographic");
    } finally {
      setIsRunning(false);
    }
  };

  const generateInfographic = async () => {
    setIsRunning(true);
    setToolOutput(null);
    setImageUrl(null);
    setImageId(null);
    try {
      const res = await fetch("/api/rag/infographic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          record_id: recordId,
          depth: infographicDepth,
          custom_prompt: showCustomPrompt && customPrompt.trim() ? customPrompt.trim() : null,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Infographic generation failed" }));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setImageUrl(data.image_url);
      setImageId(data.image_id);
      setToolMeta({
        docCount: data.document_count,
        chunkCount: data.chunk_count,
        model: data.model,
      });
      setShowInfographicSettings(false);
      await loadPreviousInfographics();
    } catch (e) {
      setToolOutput(`Error: ${e instanceof Error ? e.message : "Infographic generation failed"}`);
    } finally {
      setIsRunning(false);
    }
  };

  const generatePdf = async () => {
    setIsRunning(true);
    setToolOutput(null);
    setPdfId(null);
    setPdfMeta(null);
    try {
      const res = await fetch("/api/rag/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ record_id: recordId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "PDF generation failed" }));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setPdfId(data.pdf_id);
      setPdfMeta({
        pageCount: data.page_count,
        chunkCount: data.chunk_count,
        model: data.model,
      });
      setShowPdfSettings(false);
      await loadPreviousPdfs();
    } catch (e) {
      setToolOutput(`Error: ${e instanceof Error ? e.message : "PDF generation failed"}`);
    } finally {
      setIsRunning(false);
    }
  };

  const runTool = async (toolId: ToolId) => {
    if (documents.length === 0) {
      setToolOutput("No documents uploaded yet. Upload sources first.");
      setActiveTool(toolId);
      return;
    }

    setActiveTool(toolId);
    setIsRunning(true);
    setToolOutput(null);
    setImageUrl(null);
    setImageId(null);
    setToolMeta(null);

    // ── Export tool (client-side only) ──
    if (toolId === "export") {
      const chatExport = messages
        .map((m) => `[${m.role.toUpperCase()}] ${m.content}`)
        .join("\n\n---\n\n");
      const blob = new Blob([chatExport || "No chat history yet."], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${record?.name || "record"}-chat-export.txt`;
      a.click();
      URL.revokeObjectURL(url);
      setToolOutput("Chat history exported.");
      setIsRunning(false);
      return;
    }

    // ── Infographic Generator (show settings first) ──
    if (toolId === "infographic") {
      setIsRunning(false);
      setShowInfographicSettings(true);
      await loadPreviousInfographics();
      return;
    }

    if (toolId === "pdf") {
      setIsRunning(false);
      setShowPdfSettings(true);
      await loadPreviousPdfs();
      return;
    }

    // ── Summary Generator (full-text, dedicated endpoint) ──
    if (toolId === "summary") {
      try {
        const res = await fetch("/api/rag/summary", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ record_id: recordId }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Summary generation failed" }));
          throw new Error(err.detail || `Error ${res.status}`);
        }
        const data = await res.json();
        setToolOutput(data.summary || "No summary generated.");
        setToolMeta({
          docCount: data.document_count,
          chunkCount: data.chunk_count,
          model: data.model,
        });
      } catch (e) {
        setToolOutput(`Error: ${e instanceof Error ? e.message : "Summary generation failed"}`);
      } finally {
        setIsRunning(false);
      }
      return;
    }

    // ── Insight Generator (full-text, bypasses retrieval) ──
    if (toolId === "insights") {
      try {
        const res = await fetch("/api/rag/insights", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ record_id: recordId }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Insight generation failed" }));
          throw new Error(err.detail || `Error ${res.status}`);
        }
        const data = await res.json();
        setToolOutput(data.insights || "No insights generated.");
        setToolMeta({
          docCount: data.document_count,
          chunkCount: data.chunk_count,
          model: data.model,
        });
      } catch (e) {
        setToolOutput(`Error: ${e instanceof Error ? e.message : "Insight generation failed"}`);
      } finally {
        setIsRunning(false);
      }
      return;
    }

    // ── Outline Generator (full-text) ──
    if (toolId === "outline") {
      try {
        const res = await fetch("/api/rag/outline", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ record_id: recordId }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Outline generation failed" }));
          throw new Error(err.detail || `Error ${res.status}`);
        }
        const data = await res.json();
        setToolOutput(data.outline || "No outline generated.");
        setToolMeta({
          docCount: data.document_count,
          chunkCount: data.chunk_count,
          model: data.model,
        });
      } catch (e) {
        setToolOutput(`Error: ${e instanceof Error ? e.message : "Outline generation failed"}`);
      } finally {
        setIsRunning(false);
      }
    }
  };

  const resetTool = () => {
    setActiveTool(null);
    setToolOutput(null);
    setImageUrl(null);
    setImageId(null);
    setPdfId(null);
    setToolMeta(null);
    setPdfMeta(null);
    setShowCustomPrompt(false);
    setCustomPrompt("");
    setShowInfographicSettings(false);
    setShowPdfSettings(false);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider">Tools</h2>
        {activeTool && (
          <button
            onClick={resetTool}
            className="text-xs text-text-subtle hover:text-text"
          >
            ← All Tools
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {/* Tool list */}
        {!activeTool && (
          <div className="space-y-2">
            {TOOLS.map((tool) => (
              <button
                key={tool.id}
                onClick={() => void runTool(tool.id)}
                disabled={isRunning}
                className="w-full flex items-start gap-3 p-3 rounded-lg bg-bg-tertiary/50 hover:bg-bg-tertiary border border-transparent hover:border-border transition-colors text-left disabled:opacity-50"
              >
                <span className="text-xl shrink-0 mt-0.5">{tool.icon}</span>
                <div>
                  <p className="text-sm font-medium">{tool.name}</p>
                  <p className="text-xs text-text-subtle mt-0.5">{tool.description}</p>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Tool output */}
        {activeTool && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-lg">{TOOLS.find((t) => t.id === activeTool)?.icon}</span>
              <h3 className="font-semibold text-sm">{TOOLS.find((t) => t.id === activeTool)?.name}</h3>
            </div>

            {/* Infographic Settings UI */}
            {activeTool === "infographic" && showInfographicSettings && !isRunning && (
              <div className="space-y-4">
                {/* Depth selector */}
                <div>
                  <label className="block text-xs font-medium text-text-muted mb-2">Infographic Depth</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setInfographicDepth("standard")}
                      className={`flex-1 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                        infographicDepth === "standard"
                          ? "bg-blue-600 text-white"
                          : "bg-bg-tertiary border border-border text-text-muted hover:border-text-subtle"
                      }`}
                    >
                      Standard
                    </button>
                    <button
                      type="button"
                      onClick={() => setInfographicDepth("detailed")}
                      className={`flex-1 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                        infographicDepth === "detailed"
                          ? "bg-blue-600 text-white"
                          : "bg-bg-tertiary border border-border text-text-muted hover:border-text-subtle"
                      }`}
                    >
                      Detailed
                    </button>
                  </div>
                  <p className="text-[10px] text-text-subtle mt-1.5">
                    {infographicDepth === "detailed"
                      ? "Processes each chunk individually for comprehensive, detailed visuals"
                      : "Uses document summaries for a quick, high-level overview"}
                  </p>
                </div>

                {/* Custom prompt toggle */}
                <div>
                  <label className="flex items-center gap-2 text-xs font-medium text-text-muted cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showCustomPrompt}
                      onChange={(e) => setShowCustomPrompt(e.target.checked)}
                      className="rounded border-border"
                    />
                    Use custom prompt
                  </label>
                </div>

                {/* Custom prompt input */}
                {showCustomPrompt && (
                  <div>
                    <textarea
                      value={customPrompt}
                      onChange={(e) => setCustomPrompt(e.target.value)}
                      placeholder="Enter your custom instructions for the infographic design, style, layout, or specific elements to include..."
                      className="w-full h-28 px-3 py-2 text-xs rounded-md bg-bg-tertiary border border-border text-text placeholder-text-subtle resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    />
                    <p className="text-[10px] text-text-subtle mt-1">
                      Your prompt will be combined with the source content
                    </p>
                  </div>
                )}

                {/* Generate button */}
                <button
                  type="button"
                  onClick={generateInfographic}
                  disabled={isRunning}
                  className="w-full px-4 py-2.5 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  🎨 Generate Infographic
                </button>

                {/* Previous infographics */}
                {previousInfographics.length > 0 && (
                  <div className="mt-6 pt-4 border-t border-border">
                    <h4 className="text-xs font-medium text-text-muted mb-3">Previous Infographics</h4>
                    <div className="space-y-2">
                      {previousInfographics.map((img) => (
                        <button
                          key={img.image_id}
                          type="button"
                          onClick={() => loadPreviousImage(img.image_id)}
                          className="w-full flex items-center justify-between px-3 py-2.5 rounded-md bg-bg-tertiary border border-border hover:border-text-subtle text-left text-xs transition-colors group"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-base">🖼️</span>
                            <div>
                              <p className="text-text-muted group-hover:text-text">
                                {new Date(img.created_at).toLocaleDateString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </p>
                              <p className="text-[10px] text-text-subtle capitalize">{img.depth} depth</p>
                            </div>
                          </div>
                          <span className="text-text-subtle text-[10px]">
                            {img.model.split("/").pop()}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Loading state */}
            {isRunning && (
              <div className="flex flex-col items-center gap-3 p-8 rounded-lg bg-bg-tertiary text-sm text-text-muted">
                <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>
                  {activeTool === "insights"
                    ? "Analyzing all documents..."
                    : activeTool === "summary"
                      ? "Generating summary..."
                      : activeTool === "infographic"
                        ? "Creating infographic..."
                        : activeTool === "pdf"
                          ? "Creating PDF..."
                        : "Running..."}
                </span>
                {(activeTool === "insights" || activeTool === "summary") && (
                  <span className="text-xs text-text-subtle">This may take a moment — reading full source text</span>
                )}
                {activeTool === "infographic" && (
                  <span className="text-xs text-text-subtle">This may take up to 60 seconds — generating visual content</span>
                )}
                {activeTool === "pdf" && (
                  <span className="text-xs text-text-subtle">This may take a while — generating images for each chunk</span>
                )}
              </div>
            )}

            {/* PDF Settings UI */}
            {activeTool === "pdf" && showPdfSettings && !isRunning && (
              <div className="space-y-4">
                <p className="text-xs text-text-subtle">
                  This creates one image per chunk and compiles them into an A4 PDF.
                </p>
                <button
                  type="button"
                  onClick={generatePdf}
                  disabled={isRunning}
                  className="w-full px-4 py-2.5 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  📄 Generate PDF
                </button>

                {previousPdfs.length > 0 && (
                  <div className="mt-6 pt-4 border-t border-border">
                    <h4 className="text-xs font-medium text-text-muted mb-3">Previous PDFs</h4>
                    <div className="space-y-2">
                      {previousPdfs.map((pdf) => (
                        <button
                          key={pdf.pdf_id}
                          type="button"
                          onClick={() => handleDownloadPdf(pdf.pdf_id)}
                          className="w-full flex items-center justify-between px-3 py-2.5 rounded-md bg-bg-tertiary border border-border hover:border-text-subtle text-left text-xs transition-colors group"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-base">📄</span>
                            <div>
                              <p className="text-text-muted group-hover:text-text">
                                {new Date(pdf.created_at).toLocaleDateString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </p>
                              <p className="text-[10px] text-text-subtle">{pdf.page_count} pages</p>
                            </div>
                          </div>
                          <span className="text-text-subtle text-[10px]">
                            {pdf.model?.split("/").pop()}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Image output (infographic) */}
            {!isRunning && imageUrl && (
              <div>
                {/* Metadata bar */}
                {toolMeta && (
                  <div className="flex flex-wrap items-center gap-2 mb-3 text-[10px] text-text-subtle">
                    {toolMeta.docCount != null && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {toolMeta.docCount} doc{toolMeta.docCount !== 1 ? "s" : ""}
                      </span>
                    )}
                    {toolMeta.chunkCount != null && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {toolMeta.chunkCount} chunks
                      </span>
                    )}
                    {toolMeta.model && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {toolMeta.model.split("/").pop()}
                      </span>
                    )}
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex items-center gap-2 mb-3">
                  <button
                    type="button"
                    onClick={handleDownloadImage}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    Download Image
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setImageUrl(null);
                      setImageId(null);
                      setToolMeta(null);
                      setShowInfographicSettings(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-tertiary border border-border text-text-muted hover:text-text hover:border-text-subtle transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Generate New
                  </button>
                </div>

                {/* Image display */}
                <div
                  className="p-2 rounded-lg bg-bg-tertiary border border-border overflow-auto"
                  style={{ maxHeight: "calc(100vh - 16rem)" }}
                >
                  <img
                    src={imageUrl}
                    alt="Generated infographic"
                    className="w-full h-auto rounded shadow-lg"
                  />
                </div>
              </div>
            )}

            {/* Text output (other tools) */}
            {!isRunning && !imageUrl && !pdfId && toolOutput && (
              <div>
                {/* Metadata bar */}
                {toolMeta && (
                  <div className="flex flex-wrap items-center gap-2 mb-3 text-[10px] text-text-subtle">
                    {toolMeta.docCount != null && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {toolMeta.docCount} doc{toolMeta.docCount !== 1 ? "s" : ""}
                      </span>
                    )}
                    {toolMeta.chunkCount != null && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {toolMeta.chunkCount} chunks
                      </span>
                    )}
                    {toolMeta.model && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {toolMeta.model}
                      </span>
                    )}
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex items-center gap-2 mb-3">
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-tertiary border border-border text-text-muted hover:text-text hover:border-text-subtle transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <rect x="9" y="9" width="13" height="13" rx="2" />
                      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                    </svg>
                    {copied ? "Copied!" : "Copy"}
                  </button>
                  <button
                    type="button"
                    onClick={handleDownload}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-tertiary border border-border text-text-muted hover:text-text hover:border-text-subtle transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    Download .txt
                  </button>
                </div>

                {/* Markdown-rendered output */}
                <div
                  className="p-4 rounded-lg bg-bg-tertiary border border-border overflow-y-auto"
                  style={{ maxHeight: "calc(100vh - 16rem)" }}
                >
                  <MarkdownViewer content={toolOutput} />
                </div>
              </div>
            )}

            {/* PDF output */}
            {!isRunning && pdfId && (
              <div>
                {pdfMeta && (
                  <div className="flex flex-wrap items-center gap-2 mb-3 text-[10px] text-text-subtle">
                    {pdfMeta.pageCount != null && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {pdfMeta.pageCount} pages
                      </span>
                    )}
                    {pdfMeta.chunkCount != null && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {pdfMeta.chunkCount} chunks
                      </span>
                    )}
                    {pdfMeta.model && (
                      <span className="px-2 py-0.5 rounded-full bg-bg-tertiary border border-border">
                        {pdfMeta.model.split("/").pop()}
                      </span>
                    )}
                  </div>
                )}

                <div className="flex items-center gap-2 mb-3">
                  <button
                    type="button"
                    onClick={() => handleDownloadPdf()}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    Download PDF
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPdfId(null);
                      setPdfMeta(null);
                      setShowPdfSettings(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-tertiary border border-border text-text-muted hover:text-text hover:border-text-subtle transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Generate New
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
