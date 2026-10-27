import { useEffect, useState } from "react";
import { api } from "../api/client";

export type ServiceState = "checking" | "up" | "down";

export interface ApiStatus {
  api: ServiceState;
  database: ServiceState;
  databaseDetail?: string;
}

// Polls /health and /health/neo4j so the header always shows what is reachable.
export function useApiStatus(intervalMs = 15000): ApiStatus {
  const [status, setStatus] = useState<ApiStatus>({
    api: "checking",
    database: "checking",
  });

  useEffect(() => {
    let cancelled = false;

    async function check() {
      let apiState: ServiceState = "down";
      let dbState: ServiceState = "down";
      let detail: string | undefined;

      try {
        await api.health();
        apiState = "up";

        const neo4j = await api.neo4jHealth();
        dbState = neo4j.status === "healthy" ? "up" : "down";
        if (dbState === "down") detail = neo4j.neo4j;
      } catch {
        /* leave the states as "down" */
      }

      if (!cancelled) {
        setStatus({ api: apiState, database: dbState, databaseDetail: detail });
      }
    }

    check();
    const timer = window.setInterval(check, intervalMs);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [intervalMs]);

  return status;
}
