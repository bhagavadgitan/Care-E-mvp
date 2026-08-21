import { Link, useNavigate } from "react-router-dom";
import { LogOut, User, Building2, Truck, ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { AdminApprovals } from "@/components/AdminApprovals";

const ROLE_META = {
  HOSPITAL: { icon: Building2, label: "Hospital", blurb: "Report and resolve supply shortages across your network." },
  SUPPLIER: { icon: Truck, label: "Supplier", blurb: "Respond to supply opportunities and open requests." },
  ADMIN: { icon: ShieldCheck, label: "Administration", blurb: "Operate the network and manage organisation approvals." },
};

export default function RoleShell() {
  const { user, organisation, logout } = useAuth();
  const navigate = useNavigate();
  const meta = ROLE_META[user?.role] || ROLE_META.HOSPITAL;
  const Icon = meta.icon;

  const onLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background" data-testid={`app-shell-${user?.role?.toLowerCase()}`}>
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <span className="text-lg font-semibold tracking-tight text-primary">CARE-E</span>
            <span className="hidden rounded-sm bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary sm:inline">
              {meta.label}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted-foreground sm:inline" data-testid="shell-org-name">
              {organisation?.name || (user?.role === "ADMIN" ? "CARE-E Administration" : "CARE-E Network")}
            </span>
            <Link
              to="/app/profile"
              className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-label="Profile"
              data-testid="shell-profile-link"
            >
              <User size={18} />
            </Link>
            <Button variant="outline" size="sm" onClick={onLogout} data-testid="shell-logout-button">
              <LogOut size={15} className="mr-2" /> Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-12">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Welcome, {user?.role === "ADMIN" ? "Administrator" : user?.full_name?.split(" ")[0] || "there"}.
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">{meta.blurb}</p>
          </div>
        </div>

        {user?.role === "ADMIN" ? (
          <div className="mt-10">
            <AdminApprovals />
          </div>
        ) : (
          <div className="mt-10 rounded-lg border border-dashed border-border bg-card p-8 text-center">
            <p className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
              {meta.label} workspace
            </p>
            <h2 className="mt-2 text-lg font-semibold text-foreground">Your identity foundation is ready.</h2>
            <p className="mx-auto mt-2 max-w-lg text-sm text-muted-foreground">
              Dashboards and operational workflows (shortages, inventory, resolution, supplier
              operations) arrive in later milestones. This milestone establishes secure identity,
              organisations, facilities, roles and approvals.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
