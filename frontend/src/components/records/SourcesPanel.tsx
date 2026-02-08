import { useRef } from "react";
import { useRecordStore, type DocumentInfo } from "@/lib/store/record";

interface Props {
  recordId: string;
  onUploadClick: () => void;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(diff) || diff < 60000) return "just now";
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function SourcesPanel({ recordId, onUploadClick }: Props) {
  const { documents, isUploading, uploadDocument, fetchDocuments } = useRecordStore();
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files) return;
    for (const file of Array.from(files)) {
      await uploadDocument(recordId, file);
    }
    await fetchDocuments(recordId);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider">Sources</h2>
        <button
          onClick={() => fileRef.current?.click()}
          className="text-xs px-3 py-1 rounded-md bi-gradient text-white font-medium"
        >
          + Upload
        </button>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.docx"
          className="hidden"
          onChange={(e) => void handleFiles(e.target.files)}
        />
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isUploading && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-purple-soft/10 border border-purple-soft/30 text-sm text-purple-soft">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Uploading...
          </div>
        )}

        {documents.length === 0 && !isUploading && (
          <div className="flex flex-col items-center justify-center text-center py-12">
            <svg className="w-10 h-10 mb-3 text-text-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm text-text-subtle mb-3">No sources yet</p>
            <button
              onClick={() => fileRef.current?.click()}
              className="text-xs px-4 py-2 rounded-lg border border-border hover:border-border-strong text-text-muted hover:text-text transition-colors"
            >
              Upload first document
            </button>
          </div>
        )}

        {documents.map((doc) => (
          <DocumentCard key={doc.id} doc={doc} />
        ))}
      </div>
    </div>
  );
}

function DocumentCard({ doc }: { doc: DocumentInfo }) {
  const ext = doc.filename.split(".").pop()?.toUpperCase() || "FILE";

  const extColors: Record<string, string> = {
    PDF: "text-red-400 bg-red-400/10",
    TXT: "text-blue-400 bg-blue-400/10",
    MD: "text-green-400 bg-green-400/10",
    DOCX: "text-indigo-400 bg-indigo-400/10",
  };

  return (
    <div className="group flex items-start gap-3 p-3 rounded-lg bg-bg-tertiary/50 hover:bg-bg-tertiary border border-transparent hover:border-border transition-colors cursor-pointer">
      <div className={`shrink-0 w-9 h-9 rounded-md flex items-center justify-center text-[10px] font-bold ${extColors[ext] || "text-text-muted bg-bg-tertiary"}`}>
        {ext}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium truncate">{doc.filename}</p>
        <p className="text-xs text-text-subtle mt-0.5">
          {doc.chunk_count} chunks · {timeAgo(doc.created_at)}
        </p>
      </div>
    </div>
  );
}
