import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { useAuth } from "@/context/AuthContext";
import { FullScreenLoader } from "@/components/FullScreenLoader";

export default function AuthCallback() {
  const processed = useRef(false);
  const navigate = useNavigate();
  const { setAuth } = useAuth();

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const match = window.location.hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : null;

    (async () => {
      if (!sessionId) {
        navigate("/", { replace: true });
        return;
      }
      try {
        const res = await authApi.googleCallback(sessionId);
        window.history.replaceState(null, "", window.location.pathname);
        if (res.status === "authenticated") {
          setAuth(res.me);
          navigate("/app", { replace: true });
        } else {
          navigate("/onboarding", { replace: true, state: { email: res.email, name: res.name } });
        }
      } catch {
        window.history.replaceState(null, "", window.location.pathname);
        navigate("/?error=google", { replace: true });
      }
    })();
  }, [navigate, setAuth]);

  return <FullScreenLoader label="Completing sign-in…" />;
}
