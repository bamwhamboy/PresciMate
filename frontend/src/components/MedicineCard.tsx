import type { Medicine } from "@/lib/types";
import { Card } from "./Card";

export function MedicineCard({ medicine }: { medicine: Medicine }) {
  const details = [medicine.dosage, medicine.frequency, medicine.duration].filter(Boolean);

  return (
    <Card accent="pharmacy">
      <h3 className="font-display font-semibold text-lg text-ink">{medicine.name}</h3>
      {details.length > 0 ? (
        <p className="font-data text-sm text-pharmacy-dark mt-1 tracking-tight">
          {details.join("  \u00b7  ")}
        </p>
      ) : (
        <p className="text-sm text-ink/50 mt-1 italic">
          Dosage not specified &mdash; confirm with your doctor
        </p>
      )}
      {medicine.instructions && (
        <p className="text-sm text-ink/70 mt-2">{medicine.instructions}</p>
      )}
    </Card>
  );
}
