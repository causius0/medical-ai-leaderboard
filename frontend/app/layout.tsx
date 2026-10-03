import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedBench — Medical AI Leaderboard",
  description:
    "Comprehensive benchmark of AI models on European medical residency examinations",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
