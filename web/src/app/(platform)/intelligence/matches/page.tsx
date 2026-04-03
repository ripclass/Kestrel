import { PageFrame } from "@/components/common/page-frame";
import { MatchList } from "@/components/intelligence/match-list";
import { fetchCrossBankMatches } from "@/lib/investigation";

export default async function MatchesPage() {
  const matches = await fetchCrossBankMatches();

  return (
    <PageFrame
      eyebrow="Cross-bank overlap"
      title="Matches"
      description="Every identifier that joins reports, accounts, or alerts across institutions lands here for regulator-wide review."
    >
      <MatchList matches={matches} />
    </PageFrame>
  );
}
