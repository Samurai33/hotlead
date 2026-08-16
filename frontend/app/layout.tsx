import type { Metadata } from "next";
import { Fira_Code, Fira_Sans } from "next/font/google";
import { headers } from "next/headers";
import "./globals.css";

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

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Reading headers() opts every route into dynamic rendering (see
  // proxy.ts) -- required for the CSP nonce it sets to actually land on
  // Next's own generated inline <script> tags. A statically prerendered
  // page's HTML is fixed at build time, before any per-request nonce
  // exists, so its inline scripts would never carry one; this call is what
  // makes /login and /jobs/new (previously static) render fresh per
  // request instead. The nonce value itself isn't used here today -- no
  // custom <script>/next/script tags exist yet -- but any that get added
  // later must read it via headers().get("x-nonce") and pass it explicitly.
  await headers();

  return (
    <html lang="pt-BR" className="dark">
      <body
        className={`${firaCode.variable} ${firaSans.variable} bg-background text-text font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
