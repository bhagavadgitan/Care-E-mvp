import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Building2, Truck, Loader2 } from "lucide-react";
import { authApi } from "@/api/auth";
import { useAuth } from "@/context/AuthContext";
import { AuthShell } from "@/components/AuthShell";
import { TextField } from "@/components/AuthFields";
import { Button } from "@/components/ui/button";

export default function GoogleOnboarding() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setAuth } = useAuth();
  const identity = location.state || {};

  const [role, setRole] = useState("hospital");
  const [form, setForm] = useState({
    organisation_name: "",
    primary_facility_name: "",
    full_name: identity.name || "",
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!identity.email) navigate("/", { replace: true });
  }, [identity.email, navigate]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const onSubmit = async (ev) => {
    ev.preventDefault();
    const e = {};
    if (form.organisation_name.trim().length < 2) e.organisation_name = "Organisation name is required.";
    if (form.full_name.trim().length < 2) e.full_name = "Your name is required.";
    if (role === "hospital" && form.primary_facility_name.trim().length < 2)
      e.primary_facility_name = "Primary facility is required.";
    setErrors(e);
    if (Object.keys(e).length) return;

    setSubmitting(true);
    try {
      const me = await authApi.googleComplete({
        role: role.toUpperCase(),
        organisation_name: form.organisation_name,
        full_name: form.full_name,
        primary_facility_name: role === "hospital" ? form.primary_facility_name : undefined,
      });
      setAuth(me);
      toast.success("Account created — awaiting approval.");
      navigate("/app", { replace: true });
    } catch (err) {
      toast.error(err.message || "Could not complete onboarding.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="Complete your CARE-E account"
      subtitle={`Signed in as ${identity.email || "your Google account"}. Tell us about your organisation.`}
    >
      <div className="mb-5 grid grid-cols-2 gap-3" role="radiogroup" aria-label="Organisation type">
        {[
          { key: "hospital", label: "Hospital", icon: Building2 },
          { key: "supplier", label: "Supplier", icon: Truck },
        ].map((o) => {
          const Icon = o.icon;
          const active = role === o.key;
          return (
            <button
              key={o.key}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setRole(o.key)}
              data-testid={`onboarding-role-${o.key}`}
              className={`flex items-center gap-2 rounded-md border p-3 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring ${
                active ? "border-primary bg-primary/5 text-primary" : "border-border text-foreground hover:bg-muted"
              }`}
            >
              <Icon size={16} /> {o.label}
            </button>
          );
        })}
      </div>

      <form onSubmit={onSubmit} className="space-y-4" noValidate data-testid="onboarding-form">
        <TextField id="organisation_name" label="Organisation name" value={form.organisation_name} onChange={set("organisation_name")} error={errors.organisation_name} />
        {role === "hospital" && (
          <TextField id="primary_facility_name" label="Primary facility" value={form.primary_facility_name} onChange={set("primary_facility_name")} error={errors.primary_facility_name} />
        )}
        <TextField id="full_name" label="Your full name" value={form.full_name} onChange={set("full_name")} error={errors.full_name} />
        <Button type="submit" className="w-full" disabled={submitting} data-testid="onboarding-submit">
          {submitting && <Loader2 size={16} className="mr-2 animate-spin" />}
          Create account
        </Button>
      </form>
    </AuthShell>
  );
}
