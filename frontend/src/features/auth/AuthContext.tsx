import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  getAccessToken,
  registerUnauthorizedHandler,
  setAccessToken,
} from "../../api/client";
import { api } from "../../api/endpoints";
import type { User, UserRole } from "../../api/types";
import { env } from "../../lib/env";
import { AuthContext } from "./useAuth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  const refreshUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token && !env.useMocks) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      setAccessToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    registerUnauthorizedHandler(logout);
    void refreshUser();
  }, [logout, refreshUser]);

  const login = useCallback(
    async (email: string, password: string): Promise<User> => {
      const tokenRes = await api.login(email, password);
      setAccessToken(tokenRes.access_token);
      const me = await api.me();
      setUser(me);
      queryClient.clear();
      return me;
    },
    [queryClient],
  );

  const register = useCallback(
    async (payload: {
      name: string;
      email: string;
      password: string;
      role: UserRole;
    }): Promise<User> => {
      await api.register(payload);
      return login(payload.email, payload.password);
    },
    [login],
  );

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}
