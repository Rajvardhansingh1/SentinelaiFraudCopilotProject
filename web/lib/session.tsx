"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface SessionState {
  sessionId: string;
  callCount: number;
  incrementCallCount: () => void;
}

const SessionContext = createContext<SessionState | null>(null);

const SESSION_ID_KEY = "sentinelai_session_id";
const CALL_COUNT_KEY = "sentinelai_call_count";

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string>("");
  const [callCount, setCallCount] = useState<number>(0);

  useEffect(() => {
    let id = localStorage.getItem(SESSION_ID_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(SESSION_ID_KEY, id);
    }
    setSessionId(id);
    const storedCount = Number(localStorage.getItem(CALL_COUNT_KEY) ?? "0");
    setCallCount(Number.isFinite(storedCount) ? storedCount : 0);
  }, []);

  function incrementCallCount() {
    setCallCount((prev) => {
      const next = prev + 1;
      localStorage.setItem(CALL_COUNT_KEY, String(next));
      return next;
    });
  }

  return (
    <SessionContext.Provider value={{ sessionId, callCount, incrementCallCount }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
