import { breakable } from "./fmt";
import type { Decision, RiskDecision } from "./types";

const TONE: Record<Decision, string> = { APPROVE: "green", REVIEW: "yellow", DECLINE: "red" };

export default function VerdictPanel({ verdict }: { verdict: RiskDecision | null }) {
  if (!verdict) return <p className="meta" role="status">Send a transaction to see how it is decided.</p>;
  const passed = verdict.decision === "APPROVE";

  return (
    <div className="stack-lg" role="status">
      <div className="row">
        <span className={`tag big ${TONE[verdict.decision]}`}>{verdict.decision}</span>
        <span className="meta">Decided by the deterministic rules</span>
      </div>

      <div className="grid">
        <div className="card stack">
          <p className="meta">Layer 1 - deterministic</p>
          {verdict.rule_triggered ? (
            <p className="balance rule">{breakable(verdict.rule_triggered)}</p>
          ) : (
            <p className="meta">No rule fired.</p>
          )}
        </div>

        <div className="card stack">
          <p className="meta">Layer 2 - model score</p>
          <p className="meta">
            {passed
              ? "Not set up yet. Layer 1 passed, so this approval is not final until the model scores it."
              : "Skipped. A Layer 1 rule decided the request."}
          </p>
        </div>
      </div>
    </div>
  );
}
