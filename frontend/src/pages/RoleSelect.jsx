import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Building2, Truck, ShieldCheck, ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { FullScreenLoader } from "@/components/FullScreenLoader";

const OPTIONS = [
  {
    role: "hospital",
    icon: Building2,
    title: "Hospital / Healthcare Organisation",
    desc: "Report shortages and resolve them across your network.",
    testId: "role-hospital",
  },
  {
    role: "supplier",
    icon: Truck,
    title: "Supplier / Distributor",
    desc: "Respond to supply opportunities and open requests.",
    testId: "role-supplier",
  },
  {
    role: "admin",
    icon: ShieldCheck,
    title: "CARE-E Administration",
    desc: "Operate the network and manage approvals.",
    testId: "role-admin",
  },
];

export default function RoleSelect() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) navigate("/app", { replace: true });
  }, [loading, user, navigate]);

  if (loading) return <FullScreenLoader />;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-baseline gap-3">
            <span className="text-xl font-semibold tracking-tight text-primary">CARE-E</span>
            <span className="hidden text-sm text-muted-foreground sm:inline">
              Healthcare Supply Resolution Network
            </span>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-sm border border-primary/30 bg-primary/5 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-primary">
            <ShieldCheck size={14} /> Demonstration Data
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-16">
        <p className="text-sm font-medium uppercase tracking-wide text-muted-foreground">Sign in as</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          Choose your organisation type
        </h1>
        <p className="mt-3 max-w-xl text-sm text-muted-foreground">
          Your role is confirmed securely after you sign in. This selection simply tailors the next step.
        </p>

        <div className="mt-10 space-y-3" data-testid="role-select-list">
          {OPTIONS.map((o) => {
            const Icon = o.icon;
            return (
              <Link
                key={o.role}
                to={`/login?role=${o.role}`}
                data-testid={o.testId}
                className="group flex items-center gap-4 rounded-lg border border-border bg-card p-5 transition-colors hover:border-primary/50 hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Icon size={20} />
                </span>
                <span className="flex-1">
                  <span className="block font-medium text-foreground">{o.title}</span>
                  <span className="block text-sm text-muted-foreground">{o.desc}</span>
                </span>
                <ArrowRight size={18} className="text-muted-foreground transition-transform group-hover:translate-x-1" />
              </Link>
            );
          })}
        </div>
      </main>
    </div>
  );
}
