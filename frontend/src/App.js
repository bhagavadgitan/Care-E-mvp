import "@/App.css";
import { useQuery } from "@tanstack/react-query";
import { Activity, CircleCheck, CircleAlert, Database, RefreshCw, ShieldCheck } from "lucide-react";
import { getHealth } from "@/api/health";
import { TID } from "@/constants/testIds";

function StatusPill({ ok }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
        ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
      }`}
    >
      {ok ? <CircleCheck size={14} /> : <CircleAlert size={14} />}
      {ok ? "Connected" : "Degraded"}
    </span>
  );
}

function Row({ label, value, testId }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-3 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span data-testid={testId} className="text-sm font-medium text-foreground">
        {value}
      </span>
    </div>
  );
}

export default function App() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    retry: 1,
  });

  const dbConnected = data?.database === "connected";

  return (
    <div data-testid={TID.appShell} className="min-h-screen bg-background text-foreground">
      {/* Top institutional bar */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-baseline gap-3">
            <span
              data-testid={TID.wordmark}
              className="text-xl font-semibold tracking-tight text-primary"
            >
              CARE-E
            </span>
            <span data-testid={TID.tagline} className="hidden text-sm text-muted-foreground sm:inline">
              Healthcare Supply Resolution Network
            </span>
          </div>
          <span
            data-testid={TID.syntheticBadge}
            className="inline-flex items-center gap-1.5 rounded-sm border border-primary/30 bg-primary/5 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-primary"
          >
            <ShieldCheck size={14} />
            Demonstration · Synthetic Data
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
            Milestone M0 — Foundation
          </p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">
            Coordination layer, initialised.
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            The technical foundation for CARE-E is in place: a modular-monolith backend
            (API · service · domain · repository layers) connected to MongoDB, versioned
            under <code className="rounded bg-muted px-1.5 py-0.5 text-sm">/api/v1</code>,
            with centralized error handling and a health check. Application workflows are
            introduced in subsequent, individually authorized milestones.
          </p>
        </div>

        {/* System status panel */}
        <section
          data-testid={TID.healthPanel}
          className="mt-10 max-w-md rounded-lg border border-border bg-card p-6 shadow-sm"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-primary" />
              <h2 className="text-lg font-semibold">System Status</h2>
            </div>
            <button
              data-testid={TID.healthRefresh}
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
              aria-label="Refresh system status"
            >
              <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>

          <div className="mt-4">
            {isLoading && (
              <p data-testid={TID.healthLoading} className="py-6 text-sm text-muted-foreground">
                Checking backend connectivity…
              </p>
            )}

            {isError && (
              <p
                data-testid={TID.healthError}
                className="rounded-md bg-destructive/10 px-3 py-4 text-sm text-destructive"
                role="alert"
              >
                Unable to reach the CARE-E backend. Verify the API service is running.
              </p>
            )}

            {data && (
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <span className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Database size={15} /> Backend
                  </span>
                  <span data-testid={TID.healthStatus}>
                    <StatusPill ok={dbConnected} />
                  </span>
                </div>
                <Row label="Database" value={data.database} testId={TID.healthDb} />
                <Row label="API version" value={data.version} testId={TID.healthVersion} />
                <Row label="Environment" value={data.environment} testId={TID.healthEnv} />
                <Row label="Data mode" value={data.data_mode} testId="health-datamode-value" />
              </div>
            )}
          </div>
        </section>

        <p className="mt-10 max-w-2xl text-xs leading-relaxed text-muted-foreground">
          All data shown in CARE-E is synthetic and generated for demonstration purposes.
          No real patient, hospital, or supplier information is used.
        </p>
      </main>
    </div>
  );
}
