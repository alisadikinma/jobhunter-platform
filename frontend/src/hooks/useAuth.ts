"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import {
  clearToken,
  getUser,
  isAuthenticated,
  setToken,
  setUser,
  type CurrentUser,
} from "@/lib/auth";

export function useAuth() {
  const qc = useQueryClient();

  const login = useMutation({
    mutationFn: async (input: { email: string; password: string }) => {
      const { data } = await api.post<{ access_token: string }>(
        "/api/auth/login",
        input
      );
      setToken(data.access_token);
      const me = await api.get<CurrentUser>("/api/auth/me");
      setUser(me.data);
      qc.setQueryData(["me"], me.data);
      return me.data;
    },
  });

  const me = useQuery<CurrentUser>({
    queryKey: ["me"],
    queryFn: async () => {
      const { data } = await api.get<CurrentUser>("/api/auth/me");
      setUser(data);
      return data;
    },
    enabled: isAuthenticated(),
    initialData: getUser() ?? undefined,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  function logout() {
    clearToken();
    qc.removeQueries({ queryKey: ["me"] });
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  return {
    login,
    logout,
    me: me.data ?? null,
    isAuthenticated: isAuthenticated(),
  };
}
