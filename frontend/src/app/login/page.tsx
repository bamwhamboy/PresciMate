"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

export default function LoginPage() {
  const { token, login, signup, error, loading } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (token) router.replace("/");
  }, [token, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await signup(name, username, password);
      }
    } catch {
      // error is already surfaced via the auth context's `error` field
    }
  }

  return (
    <main className="flex-1 flex items-center justify-center bg-paper px-4 py-12 min-h-screen">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-8">
          <span
            className="inline-block w-8 h-4 rounded-full bg-marigold relative"
            aria-hidden="true"
          >
            <span className="absolute right-0 top-0 w-4 h-4 rounded-full bg-white" />
          </span>
          <h1 className="font-display text-2xl font-semibold text-pharmacy-dark">
            PresciMate
          </h1>
        </div>

        <Card torn>
          <div className="flex mb-5 border-b border-mist">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`flex-1 pb-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
                mode === "login"
                  ? "border-pharmacy text-pharmacy"
                  : "border-transparent text-ink/50"
              }`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => setMode("signup")}
              className={`flex-1 pb-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
                mode === "signup"
                  ? "border-pharmacy text-pharmacy"
                  : "border-transparent text-ink/50"
              }`}
            >
              Sign up
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "signup" && (
              <label className="block">
                <span className="text-sm font-medium text-ink/70">Your name</span>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 w-full rounded-md border border-mist px-3 py-2 text-sm
                    focus:outline-none focus:ring-2 focus:ring-pharmacy"
                />
              </label>
            )}

            <label className="block">
              <span className="text-sm font-medium text-ink/70">Username</span>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-md border border-mist px-3 py-2 text-sm
                  focus:outline-none focus:ring-2 focus:ring-pharmacy"
              />
            </label>

            <label className="block">
              <span className="text-sm font-medium text-ink/70">Password</span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-md border border-mist px-3 py-2 text-sm
                  focus:outline-none focus:ring-2 focus:ring-pharmacy"
              />
            </label>

            {error && <p className="text-sm text-clay">{error}</p>}

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Please wait..." : mode === "login" ? "Log in" : "Create account"}
            </Button>
          </form>
        </Card>

        <p className="text-xs text-center text-ink/50 mt-6">
          Your prescriptions stay private to your account &mdash; nobody else can see them.
        </p>
      </div>
    </main>
  );
}
