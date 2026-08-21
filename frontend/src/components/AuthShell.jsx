import { ShieldCheck } from "lucide-react";

export function AuthShell({ children, title, subtitle }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-primary p-12 text-primary-foreground lg:flex">
        <div>
          <span className="text-2xl font-semibold tracking-tight">CARE-E</span>
          <p className="mt-1 text-sm text-primary-foreground/70">Healthcare Supply Resolution Network</p>
        </div>
        <div>
          <h2 className="text-3xl font-semibold leading-tight">
            Coordinate shortage resolution across your network.
          </h2>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-primary-foreground/80">
            Discover feasible internal and external options, verify constraints, and approve the best
            resolution — with a human always in control.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary-foreground/70">
          <ShieldCheck size={14} /> Demonstration · Synthetic Data
        </div>
      </aside>

      <main className="flex items-center justify-center bg-background p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden">
            <span className="text-xl font-semibold text-primary">CARE-E</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
