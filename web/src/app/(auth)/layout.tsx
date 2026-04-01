export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <main className="grid min-h-screen place-items-center bg-[radial-gradient(circle_at_top,_rgba(240,180,90,0.16),_transparent_30%),linear-gradient(180deg,#09111d_0%,#101b2b_100%)] px-6 py-10">
      <div className="w-full max-w-md">{children}</div>
    </main>
  );
}
