export type Decision = "APPROVE" | "REVIEW" | "DECLINE";
export type ScenarioKind = "authentic" | "suspicious" | "fraudulent";

export interface Scenario {
  id: string;
  kind: ScenarioKind;
  label: string;
  description: string;
  amount: number; // fixed per scenario, the user does not enter it
  expect: string | null; // Layer 1 rule a clean account trips, null = none
  merchant_id: string;
  ip_address: string;
  device_fingerprint: string;
  country_code: string | null; // null = the account's own country
  card_hash: string | null;
}
export interface User {
  id: number;
  account_number: string;
  full_name: string;
  email: string;
  phone_number: string | null;
  country_code: string;
  account_status: "ACTIVE" | "FROZEN" | "SUSPENDED" | "RESTRICTED" | "CLOSED";
  risk_tier: "LOW" | "MEDIUM" | "HIGH";
  is_pep: boolean;
  created_at: string;
  updated_at: string;
}
export interface Transaction {
  id: string;
  transaction_id: string;
  user_id: number;
  amount: string | number; // Decimal serialises as a string
  currency: string;
  merchant_id: string;
  risk_score: number | null;
  rule_triggered: string | null;
  decision: string;
  is_fraud: boolean | null;
  created_at: string;
}
export type NewUser = Pick<User, "full_name" | "email" | "country_code" | "account_number">;
export interface Thresholds {
  step_up: number;
  decline: number;
  hard_limit_amount: number;
  velocity_max_tx: number;
  velocity_window_seconds: number;
}
export interface RiskDecision {
  rule_triggered: string | null; // Layer 1 rule that fired, if any
  decision: Decision;
}
export interface NewTransaction {
  transaction_id: string;
  user_id: number;
  amount: number;
  currency: string;
  merchant_id: string;
  ip_address: string;
  device_fingerprint: string;
  country_code: string;
  card_hash: string | null;
}
