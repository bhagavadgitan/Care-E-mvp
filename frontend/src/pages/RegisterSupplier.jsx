import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AuthShell } from "@/components/AuthShell";
import { TextField, PasswordField } from "@/components/AuthFields";
import { Button } from "@/components/ui/button";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function RegisterSupplier() {
  const { registerSupplier } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    organisation_name: "",
    organisation_subtype: "",
    full_name: "",
    email: "",
    password: "",
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const validate = () => {
    const e = {};
    if (form.organisation_name.trim().length < 2) e.organisation_name = "Organisation name is required.";
    if (form.full_name.trim().length < 2) e.full_name = "Your name is required.";
    if (!EMAIL_RE.test(form.email)) e.email = "Enter a valid work email.";
    if (form.password.length < 8) e.password = "Use at least 8 characters.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const onSubmit = async (ev) => {
    ev.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      await registerSupplier(form);
      toast.success("Account created — awaiting approval.");
      navigate("/app", { replace: true });
    } catch (err) {
      toast.error(err.message || "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="Register your supplier organisation"
      subtitle="Create your organisation. Access is granted after CARE-E approval."
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate data-testid="register-supplier-form">
        <TextField id="organisation_name" label="Organisation name" value={form.organisation_name} onChange={set("organisation_name")} error={errors.organisation_name} autoComplete="organization" />
        <TextField id="organisation_subtype" label="Organisation type (optional)" value={form.organisation_subtype} onChange={set("organisation_subtype")} placeholder="Distributor, Manufacturer…" />
        <TextField id="full_name" label="Your full name" value={form.full_name} onChange={set("full_name")} error={errors.full_name} autoComplete="name" />
        <TextField id="email" label="Work email" type="email" value={form.email} onChange={set("email")} error={errors.email} autoComplete="email" />
        <PasswordField id="password" label="Password" value={form.password} onChange={set("password")} error={errors.password} autoComplete="new-password" />
        <Button type="submit" className="w-full" disabled={submitting} data-testid="register-supplier-submit">
          {submitting && <Loader2 size={16} className="mr-2 animate-spin" />}
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already registered?{" "}
        <Link to="/login?role=supplier" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
