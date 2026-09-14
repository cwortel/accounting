import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { NavSidebar } from "@/components/nav-sidebar";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Green Light Boekhouding",
  description: "Accounting dashboard for a Dutch sole trader (ZZP)",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="nl"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex bg-background text-foreground">
        <NavSidebar />
        <main className="flex-1 min-w-0 overflow-x-hidden">
          <div className="mx-auto max-w-6xl p-6 md:p-8">{children}</div>
        </main>
        <Toaster />
      </body>
    </html>
  );
}
