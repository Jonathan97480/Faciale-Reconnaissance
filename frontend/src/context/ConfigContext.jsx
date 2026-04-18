import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";

const ConfigContext = createContext(null);

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    apiClient
      .getConfig()
      .then((data) => {
        if (mounted) {
          setConfig(data);
        }
      })
      .catch(() => {
        if (mounted) {
          setError("Impossible de charger la configuration.");
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const saveConfig = async (nextConfig) => {
    const saved = await apiClient.updateConfig(nextConfig);
    setConfig(saved);
    return saved;
  };

  const value = useMemo(
    () => ({ config, loading, error, saveConfig }),
    [config, loading, error]
  );

  return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}

export function useConfig() {
  const ctx = useContext(ConfigContext);
  if (!ctx) {
    throw new Error("useConfig must be used inside ConfigProvider");
  }
  return ctx;
}
