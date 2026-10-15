import type { Scenario } from "./types";

// Clean defaults. A scenario overrides only what makes it trip a rule.
// The risky values match the seed data in backend/scripts/seed_mock.py.
const base: Pick<Scenario, "merchant_id" | "ip_address" | "device_fingerprint" | "country_code" | "card_hash"> = {
  merchant_id: "merch_generic",
  ip_address: "203.0.113.10",
  device_fingerprint: "dfp_home_device",
  country_code: null,
  card_hash: null,
};
type Spec = Omit<Scenario, keyof typeof base> & Partial<typeof base>;

// `expect` is what a clean account gets. An account with its own restriction trips the account rule instead.
const specs: Spec[] = [
  { id: "coffee", kind: "authentic", label: "Morning coffee", description: "Small card payment at a local cafe, usual device and city.", amount: 4.5, expect: null, merchant_id: "merch_cafe" },
  { id: "rent", kind: "authentic", label: "Rent payment", description: "Regular monthly transfer to a known payee from the usual device.", amount: 750, expect: null, merchant_id: "merch_landlord" },

  { id: "foreign-atm", kind: "suspicious", label: "Foreign cash withdrawal", description: "ATM withdrawal in Russia, a country under step-up policy.", amount: 900, expect: "COUNTRY_STEP_UP:RU", merchant_id: "merch_atm", country_code: "RU" },
  { id: "new-device-transfer", kind: "suspicious", label: "New device transfer", description: "First payment from a device that is flagged for review.", amount: 600, expect: "ENTITY_FLAG:DEVICE_FINGERPRINT", merchant_id: "merch_transfer", device_fingerprint: "dfp_new_device_9f2c" },
  { id: "vpn-purchase", kind: "suspicious", label: "Purchase through a proxy", description: "Online order from an IP address that is flagged for review.", amount: 220, expect: "ENTITY_FLAG:IP_ADDRESS", merchant_id: "merch_electronics_online", ip_address: "203.0.113.150" },
  { id: "disputed-card", kind: "suspicious", label: "Previously disputed card", description: "Payment with a card that was flagged after an earlier dispute.", amount: 340, expect: "ENTITY_FLAG:CARD_HASH", merchant_id: "merch_electronics_online", card_hash: "card_disputed_21" },

  { id: "sanctioned-transfer", kind: "fraudulent", label: "Sanctioned country transfer", description: "Transfer sent from North Korea, a blocked country.", amount: 1200, expect: "COUNTRY_BLOCKED:KP", merchant_id: "merch_transfer", country_code: "KP" },
  { id: "account-takeover", kind: "fraudulent", label: "Account takeover", description: "Near-max transfer from a device on the block list.", amount: 9800, expect: "ENTITY_BLOCK:DEVICE_FINGERPRINT", merchant_id: "merch_transfer", device_fingerprint: "dfp_takeover_3b1a" },
  { id: "gift-card-drain", kind: "fraudulent", label: "Gift card drain", description: "High-value gift card purchase from an IP address on the block list.", amount: 2500, expect: "ENTITY_BLOCK:IP_ADDRESS", merchant_id: "merch_gift_cards", ip_address: "203.0.113.200" },
  { id: "card-testing", kind: "fraudulent", label: "Card testing", description: "Tiny payment with a stolen card hash that is on the block list.", amount: 1.0, expect: "ENTITY_BLOCK:CARD_HASH", merchant_id: "merch_digital_goods", card_hash: "card_tested_77" },
];

export const SCENARIOS: Scenario[] = specs.map((x) => ({ ...base, ...x }));
