import type { Metadata } from "next";
import Link from "next/link";
import "@xyflow/react/dist/style.css";
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
        <header className="topbar">
          <Link href="/" className="brand">
            <span className="brand-mark">↻</span> LectureLoop
          </Link>
          <span className="tagline">Find the root cause, not just the wrong answer.</span>
          {USE_MOCK && <span className="badge">Mock data</span>}
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
