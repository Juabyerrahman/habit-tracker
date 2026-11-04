import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

export default function PublicOnlyRoute() {
  const { status } = useAuth();

  if (status === "loading") {
    return <p className="p-8 text-center text-neutral-500">Loading...</p>;
  }

  if (status === "authenticated") {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
