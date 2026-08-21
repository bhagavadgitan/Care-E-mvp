import { Clock, XCircle, Ban, LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

const CONTENT = {
  PENDING: {
    icon: Clock,
    tone: "text-amber-600",
    title: "Awaiting approval",
    body: "Your organisation is awaiting CARE-E approval. You'll gain access once an administrator approves your account.",
    testId: "status-pending",
  },
  REJECTED: {
    icon: XCircle,
    tone: "text-destructive",
    title: "Access not approved",
    body: "Your organisation has not been approved for access to CARE-E. Please contact CARE-E administration for details.",
    testId: "status-rejected",
  },
  SUSPENDED: {
    icon: Ban,
    tone: "text-destructive",
    title: "Access suspended",
    body: "Access to this CARE-E account has been suspended. Please contact CARE-E administration.",
    testId: "status-suspended",
  },
};

export function AccountStatusScreen() {
  const { organisation, user, logout } = useAuth();
  const status =
    user?.account_status === "SUSPENDED" ? "SUSPENDED" : organisation?.approval_status || "PENDING";
  const c = CONTENT[status] || CONTENT.PENDING;
  const Icon = c.icon;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div
        data-testid={c.testId}
        className="w-full max-w-md rounded-lg border border-border bg-card p-8 text-center shadow-sm"
      >
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Icon className={c.tone} size={22} />
        </div>
        <h1 className="text-xl font-semibold text-foreground">{c.title}</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{c.body}</p>
        {organisation && (
          <p className="mt-4 text-xs text-muted-foreground">
            Organisation: <span className="font-medium text-foreground">{organisation.name}</span> ·{" "}
            {organisation.approval_status}
          </p>
        )}
        <Button variant="outline" className="mt-6" onClick={logout} data-testid="status-logout-button">
          <LogOut size={15} className="mr-2" /> Sign out
        </Button>
      </div>
    </div>
  );
}
