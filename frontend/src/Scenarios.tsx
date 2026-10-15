import { useState, type FormEvent } from "react";
import { breakable, money } from "./fmt";
import type { Scenario } from "./types";

const VISIBLE = 4;
const TONE = { authentic: "green", suspicious: "yellow", fraudulent: "red" } as const;

interface Props {
  scenarios: Scenario[];
  selected: Scenario | null;
  disabled: boolean;
  busy: boolean;
  onSelect: (s: Scenario) => void;
  onSubmit: () => void;
}

export default function Scenarios({ scenarios, selected, disabled, busy, onSelect, onSubmit }: Props) {
  const [all, setAll] = useState(false);
  const shown = all ? scenarios : scenarios.slice(0, VISIBLE);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (selected) onSubmit();
  };

  return (
    <form onSubmit={submit} className="stack-lg">
      <fieldset className="grid" disabled={disabled}>
        <legend className="sr-only">Transaction scenario</legend>
        {shown.map((s) => (
          <label key={s.id} className={`card pick ${selected?.id === s.id ? "on" : ""}`}>
            <input type="radio" name="scenario" className="sr-only" checked={selected?.id === s.id} onChange={() => onSelect(s)} />
            <span className={`tag ${TONE[s.kind]}`}>{s.kind}</span>
            <span className="pick-title">{s.label}</span>
            <span className="meta">{s.description}</span>
            <span className="num">{money(s.amount)}</span>
            <span className="meta">Expected: {s.expect ? breakable(s.expect) : "no Layer 1 rule"}</span>
          </label>
        ))}
        {scenarios.length === 0 && <p className="meta">No scenarios loaded.</p>}
      </fieldset>
      {scenarios.length > VISIBLE && (
        <button className="btn" type="button" aria-expanded={all} onClick={() => setAll(!all)}>
          {all ? "Show less" : `Show ${scenarios.length - VISIBLE} more`}
        </button>
      )}
      <div className="row">
        <button className="btn" type="submit" disabled={disabled || busy || !selected}>
          {busy ? "Sending..." : selected ? `Send ${money(selected.amount)}` : "Pick a transaction"}
        </button>
      </div>
    </form>
  );
}
