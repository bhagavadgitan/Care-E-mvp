import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import RoleSelect from "@/pages/RoleSelect";
import Login from "@/pages/Login";
import RegisterHospital from "@/pages/RegisterHospital";
import RegisterSupplier from "@/pages/RegisterSupplier";
import AuthCallback from "@/pages/AuthCallback";
import GoogleOnboarding from "@/pages/GoogleOnboarding";
import RoleShell from "@/pages/RoleShell";
import Profile from "@/pages/Profile";

function AppRouter() {
  const location = useLocation();
  // Handle Google OAuth return (session_id in URL fragment) before normal routing.
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<RoleSelect />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register/hospital" element={<RegisterHospital />} />
      <Route path="/register/supplier" element={<RegisterSupplier />} />
      <Route path="/onboarding" element={<GoogleOnboarding />} />
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <RoleShell />
          </ProtectedRoute>
        }
      />
      <Route
        path="/app/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster position="top-right" />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
