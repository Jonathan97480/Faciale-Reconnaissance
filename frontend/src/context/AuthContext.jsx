import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { apiClient, ApiError } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async (mounted = true) => {
    apiClient
      .getCurrentUser()
      .then((currentUser) => {
        if (mounted) {
          setUser(currentUser);
        }
      })
      .catch((error) => {
        if (mounted && !(error instanceof ApiError && error.status === 401)) {
          console.error("[AuthProvider] session bootstrap failed", error);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });
  };

  useEffect(() => {
    let mounted = true;
    refreshUser(mounted);

    return () => {
      mounted = false;
    };
  }, []);

  const login = async (username, password) => {
    await apiClient.login(username, password);
    const currentUser = await apiClient.getCurrentUser();
    setUser(currentUser);
    return currentUser;
  };

  const logout = async () => {
    try {
      await apiClient.logout();
    } finally {
      setUser(null);
    }
  };

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      logout,
      refreshUser: () => refreshUser(true),
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
