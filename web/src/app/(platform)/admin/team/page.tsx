import { PageFrame } from "@/components/common/page-frame";
import { DataTable } from "@/components/common/data-table";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { fetchAdminTeam } from "@/lib/admin";
import { requireRole } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";

export default async function TeamPage() {
  await requireRole("manager", "admin", "superadmin");
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
        <DataTable
          columns={["Name", "Designation", "Role", "Persona"]}
          rows={members.map((member) => [
            member.fullName,
            member.designation ?? "Not specified",
            <Badge key={`${member.id}-role`}>{member.role}</Badge>,
            <Badge key={`${member.id}-persona`} className="border-primary/30 bg-primary/15 text-primary">
              {member.persona}
            </Badge>,
          ])}
        />
      )}
    </PageFrame>
  );
}
