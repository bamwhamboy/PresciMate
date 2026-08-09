import type { Interaction } from "@/lib/types";

export function InteractionWarning({ interaction }: { interaction: Interaction }) {
  return (
    <div className="bg-clay/10 border-l-4 border-l-clay rounded-md p-4">
      <p className="font-semibold text-clay text-sm">
        {interaction.drug_a} + {interaction.drug_b}
        <span className="font-normal ml-2 uppercase text-xs tracking-wide">
          {interaction.severity} risk
        </span>
      </p>
      <p className="text-sm text-ink/80 mt-1">{interaction.description}</p>
    </div>
  );
}
