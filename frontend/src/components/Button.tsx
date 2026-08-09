import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
}

const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-marigold text-white hover:bg-marigold/90 shadow-sm disabled:bg-mist disabled:text-ink/40",
  secondary:
    "bg-pharmacy text-white hover:bg-pharmacy-dark disabled:bg-mist disabled:text-ink/40",
  ghost:
    "bg-transparent text-pharmacy border border-pharmacy hover:bg-pharmacy/5 disabled:border-mist disabled:text-ink/40",
};

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return (
    <button
      className={`px-5 py-2.5 rounded-md font-medium text-sm transition-colors duration-150
        focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pharmacy
        disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      {...props}
    />
  );
}
