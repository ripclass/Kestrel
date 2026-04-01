export default function PublicLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(88,166,166,0.22),_transparent_35%),linear-gradient(180deg,#09111d_0%,#0f1a2a_45%,#09111d_100%)] text-foreground">
      {children}
    </div>
  );
}
