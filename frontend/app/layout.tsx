import type { Metadata } from "next";
import { Fira_Code, Fira_Sans } from "next/font/google";
import "./globals.css";
import AuthGuard from "@/components/shared/AuthGuard";

const firaCode = Fira_Code({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-mono",
  display: "swap",
});

const firaSans = Fira_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "HotLead — Instagram Lead Extractor",
  description: "Self-hosted Instagram audience scraper and lead extractor",
  robots: "noindex, nofollow",  // private tool — no indexing
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className="dark">
      <body
        className={`${firaCode.variable} ${firaSans.variable} bg-background text-text font-sans antialiased`}
      >
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  );
}
