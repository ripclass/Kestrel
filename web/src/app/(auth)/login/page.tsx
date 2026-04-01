import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Log in to Kestrel</CardTitle>
        <CardDescription>Supabase-backed session flows land here. In scaffold mode, use the seeded demo persona env or wire real project keys.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Input placeholder="Email" type="email" />
        <Input placeholder="Password" type="password" />
        <Button className="w-full">Continue</Button>
        <div className="flex justify-between text-sm text-muted-foreground">
          <Link href="/forgot-password">Forgot password</Link>
          <Link href="/register">Register bank access</Link>
        </div>
      </CardContent>
    </Card>
  );
}
