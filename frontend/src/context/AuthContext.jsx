import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authApi } from "@/api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(null); // full /me payload
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const me = await authApi.me();
      setAuth(me);
    } catch {
      setAuth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If returning from Google OAuth, let AuthCallback establish the session first.
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const value = {
    auth,
    user: auth?.user || null,
    organisation: auth?.organisation || null,
    facilities: auth?.facilities || [],
    canAccess: auth?.can_access_app || false,
    loading,
    setAuth,
    refresh: checkAuth,
    login: async (email, password) => {
      const me = await authApi.login(email, password);
      setAuth(me);
      return me;
    },
    registerHospital: async (data) => {
      const me = await authApi.registerHospital(data);
      setAuth(me);
      return me;
    },
    registerSupplier: async (data) => {
      const me = await authApi.registerSupplier(data);
      setAuth(me);
      return me;
    },
    logout: async () => {
      try {
        await authApi.logout();
      } finally {
        setAuth(null);
      }
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
