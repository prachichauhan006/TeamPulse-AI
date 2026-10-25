import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiRequest, authorizedRequest, ApiError } from "../lib/api";
import type { TokenResponse, User } from "../types";

const ACCESS_KEY = "teampulse.access_token";
const REFRESH_KEY = "teampulse.refresh_token";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  sessionExpired: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchWithAuth: <T>(path: string, options?: RequestInit) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_KEY));
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem(REFRESH_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  }, []);

  const saveTokens = useCallback((tokens: TokenResponse) => {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
  }, []);

  const rotateRefreshToken = useCallback(async (): Promise<TokenResponse | null> => {
    if (!refreshToken) return null;
    try {
      const tokens = await apiRequest<TokenResponse>("/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      saveTokens(tokens);
      return tokens;
    } catch {
      setSessionExpired(true);
      clearAuth();
      return null;
    }
  }, [clearAuth, refreshToken, saveTokens]);

  const fetchWithAuth = useCallback(
    async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
      if (!accessToken) {
        const tokens = await rotateRefreshToken();
        if (!tokens) throw new ApiError("Authentication required", 401);
        return authorizedRequest<T>(path, options, tokens.access_token);
      }
      try {
        return await authorizedRequest<T>(path, options, accessToken);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) throw error;
        const tokens = await rotateRefreshToken();
        if (!tokens) throw error;
        return authorizedRequest<T>(path, options, tokens.access_token);
      }
    },
    [accessToken, rotateRefreshToken],
  );

  useEffect(() => {
    let mounted = true;
    async function restoreSession() {
      if (!accessToken && !refreshToken) {
        setIsLoading(false);
        return;
      }
      try {
        const currentUser = await fetchWithAuth<User>("/auth/me");
        if (mounted) setUser(currentUser);
      } catch {
        if (mounted) clearAuth();
      } finally {
        if (mounted) setIsLoading(false);
      }
    }
    void restoreSession();
    // Session restoration is intentionally run only on initial mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      setSessionExpired(false);
      const tokens = await apiRequest<TokenResponse>("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      saveTokens(tokens);
      try {
        const currentUser = await authorizedRequest<User>("/auth/me", {}, tokens.access_token);
        setUser(currentUser);
      } catch (error) {
        clearAuth();
        throw error;
      }
    },
    [clearAuth, saveTokens],
  );

  const logout = useCallback(async () => {
    if (refreshToken) {
      try {
        await apiRequest<void>("/auth/logout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {
        // Local credentials are cleared even if the server is unavailable.
      }
    }
    setSessionExpired(false);
    clearAuth();
  }, [clearAuth, refreshToken]);

  const value = useMemo(
    () => ({ user, isLoading, sessionExpired, login, logout, fetchWithAuth }),
    [user, isLoading, sessionExpired, login, logout, fetchWithAuth],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
