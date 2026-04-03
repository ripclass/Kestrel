import { TeamManagementTable } from "@/components/admin/team-management-table";
import { PageFrame } from "@/components/common/page-frame";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { fetchAdminTeam } from "@/lib/admin";
import { requireRole } from "@/lib/auth";

export default async function TeamPage() {
  const viewer = await requireRole("manager", "admin", "superadmin");
  let errorMessage: string | null = null;
  let members: Awaited<ReturnType<typeof fetchAdminTeam>> = [];

  try {
    members = await fetchAdminTeam();
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : "Unable to load team members.";
  }

  return (
    <PageFrame
      eyebrow="Administration"
      title="Team management"
      description="Invite users, assign personas, and control role-based access."
    >
      {errorMessage ? (
        <ErrorState title="Team directory unavailable" description={errorMessage} />
      ) : members.length === 0 ? (
        <EmptyState
          title="No team members found"
          description="Profiles will appear here once this organization provisions platform users."
        />
      ) : (
        <TeamManagementTable initialMembers={members} orgType={viewer.orgType} />
      )}
    </PageFrame>
  );
}
