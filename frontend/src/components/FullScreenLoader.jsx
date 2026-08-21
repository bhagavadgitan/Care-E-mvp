import { Loader2 } from "lucide-react";

export function FullScreenLoader({ label = "Loading…" }) {
  return (
    <div
      data-testid="full-screen-loader"
      className="flex min-h-screen items-center justify-center bg-background"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3 text-muted-foreground">
        <Loader2 className="animate-spin" size={18} />
        <span className="text-sm">{label}</span>
      </div>
    </div>
  );
}
