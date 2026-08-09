"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, ApiError } from "./api";

interface AuthState {
  token: string | null;
  username: string | null;
  name: string | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  signup: (name: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const STORAGE_KEY = "prescimate_auth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  // Restore session from localStorage on first load (client-side only -
  // avoids a hydration mismatch since the server has no localStorage).
  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        setToken(parsed.token);
        setUsername(parsed.username);
        setName(parsed.name);
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    setHydrated(true);
  }, []);

  function persist(t: string, u: string, n: string) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: t, username: u, name: n }));
    setToken(t);
    setUsername(u);
    setName(n);
  }

  async function login(u: string, p: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(u, p);
      persist(res.token, res.username, res.name);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong logging in");
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function signup(n: string, u: string, p: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.signup(n, u, p);
      persist(res.token, res.username, res.name);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong signing up");
      throw e;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUsername(null);
    setName(null);
  }

  return (
    <AuthContext.Provider
      value={{ token, username, name, loading: loading || !hydrated, error, login, signup, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
