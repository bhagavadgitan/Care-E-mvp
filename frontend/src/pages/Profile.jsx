import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Loader2 } from "lucide-react";
import { authApi } from "@/api/auth";
import { useAuth } from "@/context/AuthContext";
import { TextField } from "@/components/AuthFields";
import { Button } from "@/components/ui/button";

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-3 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium text-foreground">{value || "—"}</span>
    </div>
  );
}

export default function Profile() {
  const { user, organisation, facilities, setAuth } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: user?.full_name || "", job_title: user?.job_title || "" });
  const [saving, setSaving] = useState(false);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const onSave = async (ev) => {
    ev.preventDefault();
    setSaving(true);
    try {
      const me = await authApi.updateProfile(form);
      setAuth(me);
      toast.success("Profile updated.");
    } catch (err) {
      toast.error(err.message || "Could not update profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-3">
          <span className="text-lg font-semibold tracking-tight text-primary">CARE-E</span>
          <Button variant="ghost" size="sm" onClick={() => navigate("/app")} data-testid="profile-back-button">
            <ArrowLeft size={15} className="mr-2" /> Back
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10" data-testid="profile-page">
        <h1 className="text-2xl font-semibold tracking-tight">Account & profile</h1>

        <section className="mt-8 rounded-lg border border-border bg-card p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Account</h2>
          <div className="mt-2">
            <Row label="Email" value={user?.email} />
            <Row label="Role" value={user?.role} />
            <Row label="Sign-in method" value={user?.authentication_provider} />
            <Row label="Account status" value={user?.account_status} />
          </div>
        </section>

        {organisation && (
          <section className="mt-6 rounded-lg border border-border bg-card p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Organisation</h2>
            <div className="mt-2">
              <Row label="Name" value={organisation.name} />
              <Row label="Type" value={organisation.organisation_type} />
              <Row label="Approval status" value={organisation.approval_status} />
            </div>
            {facilities?.length > 0 && (
              <div className="mt-4">
                <p className="text-sm text-muted-foreground">Facilities</p>
                <ul className="mt-2 space-y-1" data-testid="profile-facilities">
                  {facilities.map((f) => (
                    <li key={f.id} className="text-sm text-foreground">
                      • {f.name} <span className="text-muted-foreground">({f.facility_type})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        <section className="mt-6 rounded-lg border border-border bg-card p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Edit profile</h2>
          <form onSubmit={onSave} className="mt-4 space-y-4" data-testid="profile-form">
            <TextField id="full_name" label="Full name" value={form.full_name} onChange={set("full_name")} />
            <TextField id="job_title" label="Role / function" value={form.job_title} onChange={set("job_title")} />
            <Button type="submit" disabled={saving} data-testid="profile-save-button">
              {saving && <Loader2 size={16} className="mr-2 animate-spin" />}
              Save changes
            </Button>
          </form>
        </section>
      </main>
    </div>
  );
}
