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
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:border focus:border-landing-foreground focus:bg-landing-bg focus:px-4 focus:py-2 focus:text-xs focus:uppercase focus:tracking-[0.18em] focus:text-landing-foreground"
      >
        Skip to main content
      </a>
      <main id="main">{children}</main>
    </div>
  );
}
