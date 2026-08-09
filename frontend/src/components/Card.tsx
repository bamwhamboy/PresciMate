import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  torn?: boolean;
  accent?: "pharmacy" | "marigold" | "clay";
  className?: string;
}

const accentBorder: Record<NonNullable<CardProps["accent"]>, string> = {
  pharmacy: "border-l-pharmacy",
  marigold: "border-l-marigold",
  clay: "border-l-clay",
};

export function Card({ children, torn = false, accent, className = "" }: CardProps) {
  return (
    <div
      className={`bg-white rounded-lg shadow-sm ${
        accent ? `border-l-4 ${accentBorder[accent]}` : "border border-mist"
      } ${torn ? "torn-edge mt-2" : ""} ${className}`}
    >
      <div className="p-5">{children}</div>
    </div>
  );
}
