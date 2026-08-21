import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { FullScreenLoader } from "@/components/FullScreenLoader";
import { AccountStatusScreen } from "@/components/AccountStatusScreen";

export function ProtectedRoute({ children }) {
  const { user, canAccess, loading } = useAuth();
  if (loading) return <FullScreenLoader label="Checking your session…" />;
  if (!user) return <Navigate to="/" replace />;
  if (!canAccess) return <AccountStatusScreen />;
  return children;
}
