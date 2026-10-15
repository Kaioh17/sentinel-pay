import { useState, type FormEvent } from "react";
import { moneyIn } from "./fmt";
import type { NewUser, Transaction, User } from "./types";

interface Props {
  user: User | null;
  txs: Transaction[];
  busy: boolean;
  onCreate: (u: NewUser) => void;
  onList: () => Promise<User[]>;
  onOpen: (id: number) => void;
  onSwitch: () => void;
}

const STATUS_TONE: Record<User["account_status"], string> = { ACTIVE: "green", RESTRICTED: "yellow", FROZEN: "red", SUSPENDED: "red", CLOSED: "red" };
const TIER_TONE: Record<User["risk_tier"], string> = { LOW: "green", MEDIUM: "yellow", HIGH: "red" };

function StateTags({ u }: { u: User }) {
  return (
    <span className="tags">
      <span className={`tag ${STATUS_TONE[u.account_status]}`}>{u.account_status}</span>
      <span className={`tag ${TIER_TONE[u.risk_tier]}`}>{u.risk_tier} risk</span>
    </span>
  );
}

const when = (iso: string) => new Date(iso).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });

export default function Account({ user, txs, busy, onCreate, onList, onOpen, onSwitch }: Props) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [country, setCountry] = useState("");
  const [users, setUsers] = useState<User[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = () => {
    setErr(null);
    onList().then(setUsers).catch((e) => setErr(e instanceof Error ? e.message : "Could not load accounts."));
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onCreate({
      full_name: name.trim(),
      email: email.trim(),
      country_code: country.trim().toUpperCase(),
      account_number: "SP" + crypto.randomUUID().replace(/-/g, "").slice(0, 12).toUpperCase(),
    });
  };

  if (!user && !users) {
    return (
      <div className="card stack">
        {err && <p className="banner" role="alert">{err}</p>}
        <button className="btn" type="button" onClick={load}>Open an account</button>
      </div>
    );
  }

  if (!user) {
    return (
      <form className="card stack" onSubmit={submit}>
        {users && users.length > 0 && (
          <>
            <p className="meta">
              Existing accounts. Account rules trip on the account itself: its status, risk tier and email domain.
              Pick a clean account to see country and entity rules fire, or a restricted one to see an account rule win.
            </p>
            <ul className="rows" aria-label="Existing accounts">
              {users.map((u) => (
                <li key={u.id}>
                  <div>
                    <span>{u.full_name}</span>
                    <p className="meta">{u.email} · {u.country_code}</p>
                  </div>
                  <StateTags u={u} />
                  <button className="btn" type="button" disabled={busy} onClick={() => onOpen(u.id)}>Open</button>
                </li>
              ))}
            </ul>
          </>
        )}
        <label htmlFor="name">Full name</label>
        <input id="name" autoComplete="off" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Amara Okafor" />
        <label htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="off" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="amara@example.com" />
        <label htmlFor="country">Country code</label>
        <input id="country" autoComplete="off" required minLength={2} maxLength={2} pattern="[A-Za-z]{2}" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="NG" />
        <button className="btn" type="submit" disabled={busy}>Create account</button>
      </form>
    );
  }

  return (
    <div className="card stack">
      <div className="row">
        <div>
          <p className="balance">{user.full_name}</p>
          <p className="meta">
            {user.account_number} · {user.email} · {user.country_code}{user.is_pep ? " · PEP" : ""}
          </p>
        </div>
        <StateTags u={user} />
        <button className="btn" type="button" disabled={busy} onClick={() => { onSwitch(); load(); }}>Switch account</button>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table aria-label="Past transactions" style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr className="meta">
              <th>Date</th>
              <th>Merchant</th>
              <th>Amount</th>
              <th>Decision</th>
              <th>Risk</th>
              <th>Rule</th>
            </tr>
          </thead>
          <tbody>
            {txs.map((t) => (
              <tr key={t.id}>
                <td>{when(t.created_at)}</td>
                <td>{t.merchant_id}</td>
                <td className="num">{moneyIn(Number(t.amount), t.currency)}</td>
                <td>{t.decision}</td>
                <td className="num">{t.risk_score === null ? "-" : `${(t.risk_score * 100).toFixed(0)}%`}</td>
                <td className="meta">{t.rule_triggered ?? "-"}</td>
              </tr>
            ))}
            {txs.length === 0 && (
              <tr>
                <td colSpan={6} className="meta">No transactions yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
