"use client";

import * as Toast from "@radix-ui/react-toast";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, X } from "lucide-react";
import * as React from "react";

type ToastType = "success" | "error" | "info";
type ToastData = { title?: string; description: string; type: ToastType };

const ToastContext = React.createContext<{
  toasts: Array<ToastData & { id: string }>;
  addToast: (t: ToastData) => void;
}>({ toasts: [], addToast: () => {} });

export function useToast() {
  const ctx = React.useContext(ToastContext);
  return {
    success: (description: string, title?: string) =>
      ctx.addToast({ description, title, type: "success" }),
    error: (description: string, title?: string) =>
      ctx.addToast({ description, title, type: "error" }),
    info: (description: string, title?: string) =>
      ctx.addToast({ description, title, type: "info" }),
  };
}

export function Toaster() {
  const [toasts, setToasts] = React.useState<Array<ToastData & { id: string; open: boolean }>>([]);
  const addToast = React.useCallback((t: ToastData) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { ...t, id, open: true }]);
    setTimeout(() => {
      setToasts((prev) => prev.map((x) => (x.id === id ? { ...x, open: false } : x)));
      setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 300);
    }, 5000);
  }, []);

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.map((x) => (x.id === id ? { ...x, open: false } : x)));
    setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 300);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast }}>
      <Toast.Provider swipeDirection="right">
        {toasts.map((t) => (
          <Toast.Root
            key={t.id}
            open={t.open}
            onOpenChange={(open) => !open && dismiss(t.id)}
            className={cn(
              "grid grid-cols-[auto_1fr_auto] gap-3 items-center rounded border p-4 animate-fade-up",
              "border-[var(--border)] bg-[var(--bg-panel)]",
              t.type === "success" && "bg-[var(--success-muted)] border-[var(--success)]/30",
              t.type === "error" && "bg-[var(--error-muted)] border-[var(--error)]/30",
              t.type === "info" && "bg-[var(--bg-elevated)]"
            )}
          >
            {t.type === "success" && <CheckCircle2 className="h-5 w-5 text-[var(--success)]" />}
            {t.type === "error" && <XCircle className="h-5 w-5 text-[var(--error)]" />}
            {t.type === "info" && null}
            <div className="min-w-0">
              {t.title && <Toast.Title className="font-semibold text-[var(--text)]">{t.title}</Toast.Title>}
              <Toast.Description className="text-sm text-[var(--text-muted)]">
                {t.description}
              </Toast.Description>
            </div>
            <Toast.Close
              className="rounded-md p-1 hover:bg-[var(--surface-hover)] text-[var(--text-muted)]"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </Toast.Close>
          </Toast.Root>
        ))}
        <Toast.Viewport className="fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:max-w-[380px] gap-2" />
      </Toast.Provider>
    </ToastContext.Provider>
  );
}
