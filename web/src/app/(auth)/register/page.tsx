import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function RegisterPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Register a bank workspace</CardTitle>
        <CardDescription>Banks continue to file in goAML. This flow scaffolds Kestrel access, scan onboarding, and peer-network posture visibility.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Input placeholder="Organization name" />
        <Input placeholder="Full name" />
        <Input placeholder="Email" type="email" />
        <Input placeholder="Password" type="password" />
        <Button className="w-full">Create access request</Button>
        <p className="text-sm text-muted-foreground">
          Already provisioned? <Link href="/login" className="text-primary">Log in</Link>
        </p>
      </CardContent>
    </Card>
  );
}
