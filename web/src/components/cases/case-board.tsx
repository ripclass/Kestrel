import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cases } from "@/lib/demo";

export function CaseBoard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Case board</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {cases.map((item) => (
          <Link key={item.id} href={`/cases/${item.id}`} className="block rounded-xl border border-border/70 bg-background/50 p-4">
            <p className="font-medium">{item.caseRef}</p>
            <p className="mt-1 text-sm text-muted-foreground">{item.title}</p>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
