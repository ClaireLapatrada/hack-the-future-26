"use client";

type CalculationModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
};

export function CalculationModal({ open, onClose, title, children }: CalculationModalProps) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="calculation-modal-title"
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative glass-card max-h-[85vh] w-full max-w-lg overflow-hidden shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <h2 id="calculation-modal-title" className="font-mono text-sm font-semibold text-textPrimary">
            How is this calculated?
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-textMuted hover:bg-white/10 hover:text-textPrimary focus:outline-none focus:ring-2 focus:ring-agentCyan"
            aria-label="Close"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <div className="overflow-y-auto px-4 py-3 font-mono text-xs text-textMuted">
          <p className="mb-2 font-medium text-textPrimary">{title}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
