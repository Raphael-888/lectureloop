import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { USE_MOCK } from "@/lib/config";

export const metadata: Metadata = {
  title: "LectureLoop",
  description: "An AI agent that finds the root cause of what you don't understand.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="hud">
          <Link href="/" className="hud-brand" title="Review what you're unsure about. Find the root cause, not just the wrong answer.">
            <span className="brand-mark">↻</span> LectureLoop
          </Link>
          {USE_MOCK && <span className="hud-badge">mock data</span>}
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
