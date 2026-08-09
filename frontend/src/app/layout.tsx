import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

const fraunces = localFont({
  src: [
    { path: "./fonts/Fraunces.ttf", style: "normal" },
    { path: "./fonts/Fraunces-Italic.ttf", style: "italic" },
  ],
  variable: "--font-display",
  display: "swap",
});

const inter = localFont({
  src: "./fonts/Inter.ttf",
  variable: "--font-body",
  display: "swap",
});

const plexMono = localFont({
  src: [
    { path: "./fonts/IBMPlexMono-Regular.ttf", weight: "400" },
    { path: "./fonts/IBMPlexMono-Medium.ttf", weight: "500" },
  ],
  variable: "--font-data",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PresciMate - Your prescription, explained",
  description:
    "Upload a photo of your prescription and get it explained in your own language.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${inter.variable} ${plexMono.variable} antialiased`}
    >
      <body className="min-h-screen flex flex-col app-background text-ink font-body">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
