import { useRef, useState } from "react";
import { FileText, Upload, X } from "lucide-react";
import { validateDeliverableFiles } from "./fileValidation";

export interface FileDropzoneProps {
  files: File[];
  onChange: (files: File[]) => void;
  helperText?: string;
}

export function FileDropzone({ files, onChange, helperText }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);

  function addFiles(list: FileList | null) {
    if (!list) return;
    const { accepted, errors: nextErrors } = validateDeliverableFiles(
      Array.from(list),
      files.length,
    );
    setErrors(nextErrors);
    if (accepted.length > 0) {
      onChange([...files, ...accepted]);
    }
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-6 text-center transition ${
          dragging ? "border-brand-600 bg-brand-50/40" : "border-ink-300 bg-canvas"
        }`}
      >
        <Upload className="h-6 w-6 text-brand-600" aria-hidden="true" />
        <p className="mt-2 text-sm font-medium text-ink-900">
          Attach local evidence files (optional)
        </p>
        <p className="mt-0.5 text-xs text-ink-600">
          {helperText ?? "Up to 5 files (5 MB each): .md, .txt, .pdf, .docx, code, or images"}
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="sr-only"
          onChange={(e) => addFiles(e.target.files)}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-3 min-h-[40px] rounded-lg border border-ink-300 bg-surface px-3.5 py-1.5 text-xs font-medium text-ink-900 hover:bg-brand-50"
        >
          Choose files
        </button>
      </div>

      {errors.length > 0 && (
        <ul role="alert" className="space-y-1 text-xs font-medium text-danger-600">
          {errors.map((err) => (
            <li key={err}>{err}</li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <ul className="space-y-1.5">
          {files.map((file, idx) => (
            <li
              key={`${file.name}-${idx}`}
              className="flex items-center justify-between rounded-lg border border-ink-300/80 bg-surface px-3 py-2 text-xs"
            >
              <span className="flex items-center gap-2 truncate text-ink-900">
                <FileText className="h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
                <span className="truncate font-medium">{file.name}</span>
                <span className="text-ink-500">({Math.max(1, Math.round(file.size / 1024))} KB)</span>
              </span>
              <button
                type="button"
                aria-label={`Remove ${file.name}`}
                onClick={() => onChange(files.filter((_, i) => i !== idx))}
                className="rounded p-1 text-ink-500 hover:text-danger-600"
              >
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
