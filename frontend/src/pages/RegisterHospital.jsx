import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AuthShell } from "@/components/AuthShell";
import { TextField, PasswordField } from "@/components/AuthFields";
import { Button } from "@/components/ui/button";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function RegisterHospital() {
  const { registerHospital } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    organisation_name: "",
    primary_facility_name: "",
    full_name: "",
    job_title: "",
    email: "",
    password: "",
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const validate = () => {
    const e = {};
    if (form.organisation_name.trim().length < 2) e.organisation_name = "Organisation name is required.";
    if (form.primary_facility_name.trim().length < 2) e.primary_facility_name = "Primary facility is required.";
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
      await registerHospital(form);
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
      title="Register your hospital"
      subtitle="Create your organisation. Access is granted after CARE-E approval."
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate data-testid="register-hospital-form">
        <TextField id="organisation_name" label="Organisation name" value={form.organisation_name} onChange={set("organisation_name")} error={errors.organisation_name} autoComplete="organization" />
        <TextField id="primary_facility_name" label="Primary facility" value={form.primary_facility_name} onChange={set("primary_facility_name")} error={errors.primary_facility_name} />
        <TextField id="full_name" label="Your full name" value={form.full_name} onChange={set("full_name")} error={errors.full_name} autoComplete="name" />
        <TextField id="job_title" label="Role / function (optional)" value={form.job_title} onChange={set("job_title")} />
        <TextField id="email" label="Work email" type="email" value={form.email} onChange={set("email")} error={errors.email} autoComplete="email" />
        <PasswordField id="password" label="Password" value={form.password} onChange={set("password")} error={errors.password} autoComplete="new-password" />
        <Button type="submit" className="w-full" disabled={submitting} data-testid="register-hospital-submit">
          {submitting && <Loader2 size={16} className="mr-2 animate-spin" />}
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already registered?{" "}
        <Link to="/login?role=hospital" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
