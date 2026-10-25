import type { RiskStatus } from "../types";
import { Badge } from "./ui";

export function RiskBadge({ status, reasons = [], showReason = false }: { status: RiskStatus; reasons?: string[]; showReason?: boolean }) {
  const tone = status === "ON_TRACK" ? "green" : status === "AT_RISK" ? "amber" : "red";
  return (
    <div className="space-y-1.5">
      <Badge tone={tone}>{status.replaceAll("_", " ")}</Badge>
      {showReason && reasons.length > 0 && (
        <ul className="space-y-1 text-xs leading-5 text-slate-600" data-testid="risk-reasons">
          {reasons.map((reason) => <li key={reason}>• {reason}</li>)}
        </ul>
      )}
    </div>
  );
}
