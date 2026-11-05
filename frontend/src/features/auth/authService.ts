import { API_BASE_URL } from "../../config/env";
import {
  apiRequest,
  clearSession,
  refreshSession,
  setSession,
  ApiError,
} from "../../api/client";
import type { SessionResponse, User } from "../../api/types";

interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

interface LoginPayload {
  email: string;
  password: string;
}

interface UserResponse {
  user: User;
}

function getBrowserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Dhaka";
  } catch {
    return "Asia/Dhaka";
  }
}

export const authService = {
  async register(payload: RegisterPayload): Promise<User> {
    const session = await apiRequest<SessionResponse>("/api/auth/register", {
      method: "POST",
      auth: false,
      retryOnExpired: false,
      body: JSON.stringify({
        ...payload,
        timezone: getBrowserTimezone(),
      }),
    });

    setSession(session);
    return session.user;
  },

  async login(payload: LoginPayload): Promise<User> {
    const session = await apiRequest<SessionResponse>("/api/auth/login", {
      method: "POST",
      auth: false,
      retryOnExpired: false,
      body: JSON.stringify(payload),
    });

    setSession(session);
    return session.user;
  },

  async restoreSession(): Promise<User | null> {
    try {
      const session = await refreshSession();
      return session.user;
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status === 401
      ) {
        clearSession();
        return null;
      }

      // Preserve the distinction between an expired session and a
      // network/server failure. The app can offer a retry when offline.
      throw error;
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiRequest<UserResponse>("/api/me");
    return response.user;
  },

  async logout(): Promise<void> {
    try {
      await apiRequest<void>("/api/auth/logout", {
        method: "POST",
        auth: false,
        retryOnExpired: false,
      });
    } finally {
      clearSession();
    }
  },

  async logoutAll(): Promise<void> {
    try {
      await apiRequest<void>("/api/auth/logout-all", {
        method: "POST",
      });
    } finally {
      clearSession();
    }
  },

  startGoogleLogin(): void {
    const timezone = encodeURIComponent(getBrowserTimezone());

    window.location.assign(
      `${API_BASE_URL}/auth/google/login?tz=${timezone}&return=app`,
    );
  },
};
