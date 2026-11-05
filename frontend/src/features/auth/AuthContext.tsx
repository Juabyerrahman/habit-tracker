import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { User } from "../../api/types";
import { authService } from "./authService";

type AuthStatus =
  | "loading"
  | "authenticated"
  | "unauthenticated"
  | "error";

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (
    name: string,
    email: string,
    password: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  retryRestore: () => Promise<void>;
  startGoogleLogin: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const restore = useCallback(async () => {
    setStatus("loading");
    setError(null);

    try {
      const restoredUser = await authService.restoreSession();

      setUser(restoredUser);
      setStatus(restoredUser ? "authenticated" : "unauthenticated");
    } catch (err) {
      setUser(null);
      setStatus("error");
      setError(
        err instanceof Error
          ? err.message
          : "Unable to restore your session.",
      );
    }
  }, []);

  useEffect(() => {
    void restore();
  }, [restore]);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      const loggedInUser = await authService.login({ email, password });
      setUser(loggedInUser);
      setStatus("authenticated");
    },
    [],
  );

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      setError(null);
      const newUser = await authService.register({
        name,
        email,
        password,
      });
      setUser(newUser);
      setStatus("authenticated");
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const logoutAll = useCallback(async () => {
    try {
      await authService.logoutAll();
    } finally {
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const startGoogleLogin = useCallback(() => {
    authService.startGoogleLogin();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      error,
      login,
      register,
      logout,
      logoutAll,
      retryRestore: restore,
      startGoogleLogin,
    }),
    [
      user,
      status,
      error,
      login,
      register,
      logout,
      logoutAll,
      restore,
      startGoogleLogin,
    ],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider.");
  }

  return context;
}
