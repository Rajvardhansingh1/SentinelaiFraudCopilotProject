import type { Metadata } from "next";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import { SidebarNav } from "@/components/layout/sidebar-nav";

export const metadata: Metadata = {
  title: "SentinelAI + Fraud Copilot",
  description: "SentinelAI red-team playground, receipt review, and eval dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg-base text-text-primary antialiased">
        <SessionProvider>
          <div className="flex min-h-screen">
            <SidebarNav />
            <main className="flex-1 p-6">{children}</main>
          </div>
        </SessionProvider>
      </body>
    </html>
  );
}
