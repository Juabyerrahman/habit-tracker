
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

export default function AuthCallbackPage() {
  const { status, error, retryRestore } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (status === "authenticated") {
      navigate("/", { replace: true });
    } else if (status === "unauthenticated") {
      navigate("/login", { replace: true });
    }
  }, [status, navigate]);

  if (status === "error") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-white p-6">
        <h1 className="text-xl font-semibold text-neutral-900">
          Authentication failed
        </h1>
        <p className="text-sm text-neutral-600">
          {error || "Unable to complete Google sign-in."}
        </p>
        <button
          onClick={() => void retryRestore()}
          className="rounded-lg bg-neutral-900 px-5 py-2 text-white"
        >
          Try again
        </button>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-white">
      <div className="text-center">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900" />
        <h1 className="text-lg font-semibold text-neutral-900">
          Completing Google sign-in
        </h1>
        <p className="mt-2 text-sm text-neutral-500">
          Please wait while we restore your session.
        </p>
      </div>
    </main>
  );
}
