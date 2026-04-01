import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function CaseNotes() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Notes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>Counterparty KYC packet requested from Sonali Bank.</p>
        <p>Wallet beneficiary mapping suggests third-party collection activity.</p>
      </CardContent>
    </Card>
  );
}
