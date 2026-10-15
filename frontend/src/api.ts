import type { NewTransaction, NewUser, RiskDecision, Thresholds, Transaction, User } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is the backend running?");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : res.statusText;
    throw new ApiError(res.status, res.status === 501 ? "This endpoint is not implemented yet." : detail);
  }
  return res.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const api = {
  createUser: (u: NewUser) => call<User>("/users", json("POST", u)),
  users: () => call<User[]>("/users/").catch((e) => (e instanceof ApiError && e.status === 404 ? [] : Promise.reject(e))),
  thresholds: () => call<Thresholds>("/config/thresholds"),
  setThresholds: (t: Thresholds) => call<Thresholds>("/config/thresholds", json("PUT", t)),
  createTransaction: (t: NewTransaction) => call<RiskDecision>("/transactions", json("POST", t)),
  transactions: (id: number) => call<Transaction[]>(`/users/${id}/transactions`),
  user: (id: number) => call<User>(`/users/${id}`),
};
