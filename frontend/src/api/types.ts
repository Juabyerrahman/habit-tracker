export interface User {
  id: number;
  email: string;
  email_verified: boolean;
  name: string;
  timezone: string;
  week_starts_on: number;
  auth_providers: string[];
  created_at: string;
}

export interface SessionResponse {
  user: User;
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface ApiSuccess<T> {
  data: T;
}
