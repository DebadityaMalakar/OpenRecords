import { useCallback, useRef, useState } from "react";
import { useRecordStore } from "@/lib/store/record";

interface Props {
  recordId: string;
  onComplete: () => void;
}

const STEPS = ["Welcome", "Upload Sources", "Reference Links", "Settings", "Finish"] as const;

export default function OnboardingWizard({ recordId, onComplete }: Props) {
  const [step, setStep] = useState(0);
  const { uploadDocument, isUploading, documents, fetchDocuments } = useRecordStore();
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files) return;
      for (const file of Array.from(files)) {
        const ok = await uploadDocument(recordId, file);
        if (ok) setUploadedFiles((prev) => [...prev, file.name]);
      }
      await fetchDocuments(recordId);
    },
    [recordId, uploadDocument, fetchDocuments]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      void handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-2xl surface-secondary rounded-2xl border border-border p-8 bi-glow">
        {/* Progress */}
        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-2 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  i <= step
                    ? "bi-gradient text-white"
                    : "bg-bg-tertiary text-text-muted border border-border"
                }`}
              >
                {i < step ? "✓" : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`h-0.5 flex-1 ${
                    i < step ? "bg-purple-soft" : "bg-border"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step 0: Welcome */}
        {step === 0 && (
          <div className="text-center">
            <h1 className="text-3xl font-bold mb-4">Welcome to your workspace</h1>
            <p className="text-text-muted mb-2">
              This is where you&apos;ll upload knowledge sources, query them with AI, and generate insights.
            </p>
            <p className="text-text-subtle text-sm mb-8">
              Let&apos;s set things up in a few quick steps.
            </p>
            <button onClick={next} className="px-8 py-3 bi-gradient rounded-lg font-bold text-white">
              Continue
            </button>
          </div>
        )}

        {/* Step 1: Upload */}
        {step === 1 && (
          <div>
            <h2 className="text-2xl font-bold mb-2">Upload your sources</h2>
            <p className="text-text-muted mb-6 text-sm">
              Drag &amp; drop files or click to browse. Supports PDF, TXT, MD, DOCX.
            </p>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
                dragOver
                  ? "border-purple-soft bg-purple-soft/10"
                  : "border-border hover:border-border-strong"
              }`}
            >
              <input
                ref={fileRef}
                type="file"
                multiple
                accept=".pdf,.txt,.md,.docx"
                className="hidden"
                onChange={(e) => void handleFiles(e.target.files)}
              />
              <svg className="w-12 h-12 mx-auto mb-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {isUploading ? (
                <p className="text-purple-soft font-medium">Uploading...</p>
              ) : (
                <p className="text-text-muted">Drop files here or click to browse</p>
              )}
            </div>

            {uploadedFiles.length > 0 && (
              <div className="mt-4 space-y-2">
                {uploadedFiles.map((name) => (
                  <div key={name} className="flex items-center gap-2 text-sm text-text-muted bg-bg-tertiary rounded-lg px-3 py-2">
                    <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {name}
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-between mt-8">
              <button onClick={prev} className="px-6 py-2 rounded-lg border border-border text-text-muted hover:text-text">
                Back
              </button>
              <button onClick={next} className="px-6 py-2 bi-gradient rounded-lg font-bold text-white">
                {uploadedFiles.length > 0 ? "Continue" : "Skip"}
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Reference Links (optional) */}
        {step === 2 && (
          <div>
            <h2 className="text-2xl font-bold mb-2">Add reference links</h2>
            <p className="text-text-muted mb-6 text-sm">
              Optional — add URLs to web sources you&apos;d like to reference.
            </p>
            <p className="text-text-subtle text-sm italic mb-8">
              Reference link indexing is coming soon. You can skip this step for now.
            </p>
            <div className="flex justify-between mt-8">
              <button onClick={prev} className="px-6 py-2 rounded-lg border border-border text-text-muted hover:text-text">
                Back
              </button>
              <button onClick={next} className="px-6 py-2 bi-gradient rounded-lg font-bold text-white">
                Skip
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Settings (optional) */}
        {step === 3 && (
          <div>
            <h2 className="text-2xl font-bold mb-2">Initial settings</h2>
            <p className="text-text-muted mb-6 text-sm">
              Optional — you can change these later from the workspace.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">Chat Model</label>
                <input
                  type="text"
                  defaultValue="moonshotai/kimi-k2.5"
                  readOnly
                  className="w-full px-4 py-2 rounded-lg bg-bg-tertiary border border-border text-text text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">Embed Model</label>
                <input
                  type="text"
                  defaultValue="text-embedding-3-large"
                  readOnly
                  className="w-full px-4 py-2 rounded-lg bg-bg-tertiary border border-border text-text text-sm"
                />
              </div>
            </div>
            <div className="flex justify-between mt-8">
              <button onClick={prev} className="px-6 py-2 rounded-lg border border-border text-text-muted hover:text-text">
                Back
              </button>
              <button onClick={next} className="px-6 py-2 bi-gradient rounded-lg font-bold text-white">
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Finish */}
        {step === 4 && (
          <div className="text-center">
            <h1 className="text-3xl font-bold mb-4">You&apos;re all set!</h1>
            <p className="text-text-muted mb-8">
              Your workspace is ready. Start querying your documents with AI.
            </p>
            <button onClick={onComplete} className="px-8 py-3 bi-gradient rounded-lg font-bold text-white">
              Enter Workspace
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
