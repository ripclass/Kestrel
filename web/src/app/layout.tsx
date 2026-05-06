import type { Metadata } from "next";
import { Geist, Geist_Mono, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://kestrelfin.com",
  ),
  title: {
    default: "Kestrel — Financial crime intelligence for Bangladesh's banks",
    template: "%s · Kestrel",
  },
  description:
    "Pattern detection, cross-bank entity intelligence, AI-drafted STRs, real-time transaction scoring, and goAML interoperability. Billable in BDT, deployable on local infrastructure.",
  applicationName: "Kestrel",
  authors: [{ name: "Enso Intelligence Inc." }],
  openGraph: {
    type: "website",
    siteName: "Kestrel",
    title: "Kestrel — Financial crime intelligence for Bangladesh's banks",
    description:
      "Pattern detection, cross-bank entity intelligence, AI-drafted STRs, real-time transaction scoring, and goAML interoperability. Billable in BDT.",
    url: "/",
    locale: "en_GB",
  },
  twitter: {
    card: "summary_large_image",
    title: "Kestrel — Financial crime intelligence for Bangladesh's banks",
    description:
      "Pattern detection, cross-bank entity intelligence, AI-drafted STRs, real-time transaction scoring, and goAML interoperability.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${plexSans.variable} ${plexMono.variable} dark`}
    >
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
