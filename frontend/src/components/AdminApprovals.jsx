import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, CheckCircle2, XCircle, Ban, RotateCcw } from "lucide-react";
import { orgApi } from "@/api/org";
import { Button } from "@/components/ui/button";

const STATUS_STYLES = {
  PENDING: "bg-amber-50 text-amber-700",
  APPROVED: "bg-emerald-50 text-emerald-700",
  REJECTED: "bg-red-50 text-red-700",
  SUSPENDED: "bg-red-50 text-red-700",
};

export function AdminApprovals() {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await orgApi.list();
      setOrgs(data.organisations || []);
    } catch (e) {
      toast.error(e.message || "Could not load organisations.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (id, status) => {
    setBusy(`${id}:${status}`);
    try {
      await orgApi.updateStatus(id, status);
      toast.success(`Organisation ${status.toLowerCase()}.`);
      await load();
    } catch (e) {
      toast.error(e.message || "Action failed.");
    } finally {
      setBusy(null);
    }
  };

  const actionsFor = (o) => {
    if (o.approval_status === "PENDING")
      return [
        { label: "Approve", status: "APPROVED", icon: CheckCircle2, variant: "default" },
        { label: "Reject", status: "REJECTED", icon: XCircle, variant: "outline" },
      ];
    if (o.approval_status === "APPROVED")
      return [{ label: "Suspend", status: "SUSPENDED", icon: Ban, variant: "outline" }];
    if (o.approval_status === "SUSPENDED")
      return [{ label: "Reactivate", status: "APPROVED", icon: RotateCcw, variant: "outline" }];
    return [];
  };

  return (
    <section
      data-testid="admin-approvals"
      className="rounded-lg border border-border bg-card"
    >
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Organisation approvals
        </h2>
        <Button variant="ghost" size="sm" onClick={load} data-testid="approvals-refresh">
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 px-5 py-10 text-sm text-muted-foreground">
          <Loader2 size={16} className="animate-spin" /> Loading organisations…
        </div>
      ) : orgs.length === 0 ? (
        <p className="px-5 py-10 text-sm text-muted-foreground">No organisations yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th scope="col" className="px-5 py-3 font-medium">Organisation</th>
                <th scope="col" className="px-5 py-3 font-medium">Type</th>
                <th scope="col" className="px-5 py-3 font-medium">Status</th>
                <th scope="col" className="px-5 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {orgs.map((o) => (
                <tr key={o.id} className="border-b border-border/60 last:border-0" data-testid={`org-row-${o.id}`}>
                  <td className="px-5 py-3 font-medium text-foreground">{o.name}</td>
                  <td className="px-5 py-3 text-muted-foreground">{o.organisation_type}</td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[o.approval_status] || ""}`}>
                      {o.approval_status}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex justify-end gap-2">
                      {actionsFor(o).map((a) => {
                        const Icon = a.icon;
                        const key = `${o.id}:${a.status}`;
                        return (
                          <Button
                            key={a.status}
                            size="sm"
                            variant={a.variant}
                            disabled={busy === key}
                            onClick={() => act(o.id, a.status)}
                            data-testid={`org-action-${a.status.toLowerCase()}-${o.id}`}
                          >
                            {busy === key ? (
                              <Loader2 size={14} className="mr-1.5 animate-spin" />
                            ) : (
                              <Icon size={14} className="mr-1.5" />
                            )}
                            {a.label}
                          </Button>
                        );
                      })}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
