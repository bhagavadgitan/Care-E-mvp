import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AuthShell } from "@/components/AuthShell";
import { TextField, PasswordField, GoogleButton } from "@/components/AuthFields";
import { Button } from "@/components/ui/button";

const HEADINGS = {
  hospital: "Hospital sign in",
  supplier: "Supplier sign in",
  admin: "CARE-E Administration sign in",
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const [params] = useSearchParams();
  const role = params.get("role") || "hospital";
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const e = {};
    if (!EMAIL_RE.test(email)) e.email = "Enter a valid email address.";
    if (!password) e.password = "Enter your password.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const onSubmit = async (ev) => {
    ev.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/app", { replace: true });
    } catch (err) {
      toast.error(err.message || "Sign in failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell title={HEADINGS[role] || HEADINGS.hospital} subtitle="Sign in to your CARE-E account.">
      <form onSubmit={onSubmit} className="space-y-5" noValidate data-testid="login-form">
        <TextField
          id="email"
          label="Work email"
          type="email"
          value={email}
          onChange={setEmail}
          error={errors.email}
          autoComplete="email"
          placeholder="you@organisation.org"
        />
        <PasswordField id="password" value={password} onChange={setPassword} error={errors.password} />
        <Button type="submit" className="w-full" disabled={submitting} data-testid="login-submit-button">
          {submitting && <Loader2 size={16} className="mr-2 animate-spin" />}
          Sign in
        </Button>
      </form>

      <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" /> OR <span className="h-px flex-1 bg-border" />
      </div>
      <GoogleButton />

      {role !== "admin" && (
        <p className="mt-8 text-center text-sm text-muted-foreground">
          New to CARE-E?{" "}
          <Link
            to={`/register/${role}`}
            className="font-medium text-primary hover:underline"
            data-testid="login-register-link"
          >
            Register your {role === "supplier" ? "supplier" : "hospital"}
          </Link>
        </p>
      )}
      <p className="mt-3 text-center text-sm">
        <Link to="/" className="text-muted-foreground hover:underline" data-testid="login-back-link">
          ← Choose a different role
        </Link>
      </p>
    </AuthShell>
  );
}
