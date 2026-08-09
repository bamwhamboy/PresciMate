import type { Grounding } from "@/lib/types";

export function GroundingWarning({ grounding }: { grounding: Grounding }) {
  if (!grounding.flagged) return null;

  return (
    <div className="bg-marigold/10 border-l-4 border-l-marigold rounded-md p-4 text-sm">
      <p className="font-semibold text-marigold">
        Double-check these numbers with your doctor or pharmacist
      </p>
      <p className="text-ink/80 mt-1">
        This explanation mentions details that don&rsquo;t appear on your
        prescription or in the reference material:{" "}
        <span className="font-data">{grounding.ungrounded_claims.join(", ")}</span>
      </p>
    </div>
  );
}
