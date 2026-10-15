import { useCallback, useEffect, useState } from "react";
import Account from "./Account";
import { api } from "./api";
import Reveal from "./Reveal";
import Scenarios from "./Scenarios";
import ThresholdsPanel from "./ThresholdsPanel";
import { SCENARIOS } from "./scenarioData";
import type { NewUser, RiskDecision, Scenario, Thresholds, Transaction, User } from "./types";
import VerdictPanel from "./VerdictPanel";

const SESSION_KEY = "sentinelpay.session";
const SESSION_MS = 2 * 60 * 60 * 1000;

const saveSession = (id: number) => {
  try { localStorage.setItem(SESSION_KEY, JSON.stringify({ id, exp: Date.now() + SESSION_MS })); } catch { /* storage unavailable */ }
};
const clearSession = () => {
  try { localStorage.removeItem(SESSION_KEY); } catch { /* storage unavailable */ }
};
const loadSession = (): number | null => {
  try {
    const s = JSON.parse(localStorage.getItem(SESSION_KEY) ?? "null");
    if (s && s.exp > Date.now()) return Number(s.id);
    localStorage.removeItem(SESSION_KEY);
  } catch { /* storage unavailable */ }
  return null;
};

const msg = (e: unknown) => (e instanceof Error ? e.message : "Something went wrong.");

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [selected, setSelected] = useState<Scenario | null>(null);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [verdict, setVerdict] = useState<RiskDecision | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(msg(e));
    } finally {
      setBusy(false);
    }
  }, []);

  // The server saves the row after it answers, so a refetch right after a send can miss it. Wait briefly for `expect`.
  const open = async (id: number, expect?: string) => {
    for (let i = 0; ; i++) {
      const [u, t] = await Promise.all([api.user(id), api.transactions(id)]);
      if (expect && i < 5 && !t.some((x) => x.transaction_id === expect)) {
        await new Promise((r) => setTimeout(r, 200));
        continue;
      }
      saveSession(u.id);
      setUser(u);
      setTxs(t);
      return;
    }
  };

  useEffect(() => {
    api.thresholds().then(setThresholds).catch((e) => setError(msg(e)));
    const id = loadSession();
    if (id) open(id).catch(() => localStorage.removeItem(SESSION_KEY));
  }, []);

  return (
    <>
      <header className="nav">
        <span className="brand">SentinelPay</span>
        <span className="meta">Fraud decision simulator</span>
      </header>

      <main>
        <section className="hero">
          <h1>
            Send a transaction. See exactly <span className="accent">why it was decided</span>
          </h1>
          <p className="lede">
            Every payment passes through fixed rules first, then a trained model. Pick an authentic, suspicious or fraudulent
            transaction and follow it through both layers.
          </p>
        </section>

        {error && <p className="banner" role="alert">{error}</p>}

        <Reveal>
          <h2>1. Open an <span className="accent">account</span></h2>
          <Account
            user={user}
            txs={txs}
            busy={busy}
            onCreate={(n: NewUser) => run(async () => { await open((await api.createUser(n)).id); setVerdict(null); })}
            onList={() => api.users()}
            onOpen={(id) => run(async () => { await open(id); setVerdict(null); })}
            onSwitch={() => { clearSession(); setUser(null); setTxs([]); setVerdict(null); }}
          />
        </Reveal>

        <Reveal>
          <h2>2. Choose a <span className="accent">transaction</span></h2>
          <Scenarios
            scenarios={SCENARIOS}
            selected={selected}
            disabled={!user}
            busy={busy}
            onSelect={setSelected}
            onSubmit={() =>
              run(async () => {
                if (!user || !selected) return;
                const transaction_id = crypto.randomUUID();
                setVerdict(
                  await api.createTransaction({
                    transaction_id,
                    user_id: user.id,
                    amount: selected.amount,
                    currency: "USD",
                    merchant_id: selected.merchant_id,
                    ip_address: selected.ip_address,
                    device_fingerprint: selected.device_fingerprint,
                    country_code: selected.country_code ?? user.country_code,
                    card_hash: selected.card_hash,
                  }),
                );
                await open(user.id, transaction_id);
              })
            }
          />
        </Reveal>

        <Reveal>
          <h2>3. Read the <span className="accent">verdict</span></h2>
          <VerdictPanel verdict={verdict} />
        </Reveal>

        <Reveal>
          <h2>4. Tune the <span className="accent">thresholds</span></h2>
          <ThresholdsPanel value={thresholds} busy={busy} onSave={(t) => run(async () => setThresholds(await api.setThresholds(t)))} />
        </Reveal>
      </main>

      <footer className="foot meta">Simulation only. No real money or card data is used.</footer>
    </>
  );
}
