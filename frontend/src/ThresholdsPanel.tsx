import { useEffect, useState, type FormEvent } from "react";
import { pct } from "./fmt";
import type { Thresholds } from "./types";

interface Props {
  value: Thresholds | null;
  busy: boolean;
  onSave: (t: Thresholds) => void;
}

export default function ThresholdsPanel({ value, busy, onSave }: Props) {
  const [draft, setDraft] = useState<Thresholds | null>(value);
  useEffect(() => setDraft(value), [value]);
  if (!draft) return <p className="meta">Thresholds unavailable.</p>;

  const ordered = draft.step_up < draft.decline;
  const set = (k: keyof Thresholds, v: number) => setDraft({ ...draft, [k]: v });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (ordered) onSave(draft);
  };

  return (
    <form className="card stack-lg" onSubmit={submit}>
      <div className="stack">
        <label htmlFor="step">Step-up from {pct(draft.step_up)}</label>
        <input id="step" type="range" min={0} max={1} step={0.01} value={draft.step_up} onChange={(e) => set("step_up", Number(e.target.value))} />
      </div>
      <div className="stack">
        <label htmlFor="decline">Decline from {pct(draft.decline)}</label>
        <input id="decline" type="range" min={0} max={1} step={0.01} value={draft.decline} onChange={(e) => set("decline", Number(e.target.value))} />
      </div>
      <div className="stack">
        <label htmlFor="limit">Hard limit per transaction (USD)</label>
        <input id="limit" type="number" min={1} value={draft.hard_limit_amount} onChange={(e) => set("hard_limit_amount", Number(e.target.value))} />
      </div>
      {!ordered && <p className="error" role="alert">Step-up must be lower than decline.</p>}
      <button className="btn" type="submit" disabled={busy || !ordered}>Apply thresholds</button>
    </form>
  );
}
