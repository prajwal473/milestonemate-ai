import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { Button } from "./Button";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function Modal({ open, onClose, title, description, children, footer }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 p-4 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="w-full max-w-lg rounded-xl border border-ink-300/70 bg-surface shadow-xl">
        <div className="flex items-start justify-between border-b border-ink-300/60 px-5 py-4">
          <div>
            <h2 id="modal-title" className="text-lg font-semibold text-ink-900">
              {title}
            </h2>
            {description && <p className="mt-0.5 text-sm text-ink-600">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="rounded-lg p-1.5 text-ink-500 hover:bg-canvas hover:text-ink-900"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-ink-300/60 bg-canvas/60 px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  loading?: boolean;
  children?: ReactNode;
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  danger = false,
  loading = false,
  children,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm text-ink-600">{message}</p>
      {children && <div className="mt-3">{children}</div>}
    </Modal>
  );
}

