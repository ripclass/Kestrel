import { IBM_Plex_Mono, JetBrains_Mono } from "next/font/google";

const displayFont = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-landing-display",
});

const bodyFont = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-landing-body",
});

export default function PublicLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div
      className={`${displayFont.variable} ${bodyFont.variable} min-h-screen bg-landing-bg text-landing-foreground font-[family-name:var(--font-landing-body)]`}
    >
      {children}
    </div>
  );
}
