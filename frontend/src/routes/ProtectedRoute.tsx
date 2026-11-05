import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

export default function ProtectedRoute() {
  const { status, retryRestore } = useAuth();

  if (status === "loading") {
    return <p className="p-8 text-center text-neutral-500">Restoring session...</p>;
  }

  if (status === "error") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
        <p className="text-neutral-700">Unable to verify your session.</p>
        <button
          onClick={() => void retryRestore()}
          className="rounded-lg bg-neutral-900 px-5 py-2 text-white"
        >
          Retry
        </button>
      </main>
    );
  }

  if (status !== "authenticated") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
