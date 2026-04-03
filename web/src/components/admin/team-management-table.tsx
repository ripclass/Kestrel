"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { AdminTeamMember, OrgType, Persona, Role } from "@/types/domain";
import type { AdminTeamMutationResponse } from "@/types/api";

type TeamDraft = {
  role: Role;
  persona: Persona;
  designation: string;
};

const ROLE_OPTIONS: Role[] = ["superadmin", "admin", "manager", "analyst", "viewer"];

function personaOptions(orgType: OrgType): Persona[] {
  if (orgType === "regulator") {
    return ["bfiu_analyst", "bfiu_director"];
  }
  return ["bank_camlco"];
}

function toDraft(member: AdminTeamMember): TeamDraft {
  return {
    role: member.role,
    persona: member.persona,
    designation: member.designation ?? "",
  };
}

function sameDraft(left: TeamDraft, right: TeamDraft) {
  return (
    left.role === right.role &&
    left.persona === right.persona &&
    left.designation === right.designation
  );
}

export function TeamManagementTable({
  initialMembers,
  orgType,
}: {
  initialMembers: AdminTeamMember[];
  orgType: OrgType;
}) {
  const [members, setMembers] = useState(initialMembers);
  const [drafts, setDrafts] = useState<Record<string, TeamDraft>>(
    Object.fromEntries(initialMembers.map((member) => [member.id, toDraft(member)])),
  );
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateDraft(memberId: string, patch: Partial<TeamDraft>) {
    setDrafts((current) => ({
      ...current,
      [memberId]: { ...current[memberId], ...patch },
    }));
  }

  function resetDraft(member: AdminTeamMember) {
    setDrafts((current) => ({
      ...current,
      [member.id]: toDraft(member),
    }));
  }

  async function saveMember(member: AdminTeamMember) {
    const draft = drafts[member.id];
    setPendingId(member.id);
    setNotice(null);
    setError(null);

    const response = await fetch(`/api/admin/team/${encodeURIComponent(member.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role: draft.role,
        persona: draft.persona,
        designation: draft.designation.trim() === "" ? null : draft.designation.trim(),
      }),
    });
    const payload = await readResponsePayload<AdminTeamMutationResponse>(response);

    if (!response.ok) {
      setError(detailFromPayload(payload, "Unable to update team member."));
      setPendingId(null);
      return;
    }

    const updatedMember = (payload as AdminTeamMutationResponse).member;
    setMembers((current) => current.map((entry) => (entry.id === updatedMember.id ? updatedMember : entry)));
    setDrafts((current) => ({
      ...current,
      [updatedMember.id]: toDraft(updatedMember),
    }));
    setNotice(`${updatedMember.fullName} updated.`);
    setPendingId(null);
  }

  return (
    <div className="space-y-4">
      {notice ? <p className="text-sm text-primary">{notice}</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="grid gap-4">
        {members.map((member) => {
          const draft = drafts[member.id];
          const dirty = !sameDraft(draft, toDraft(member));

          return (
            <Card key={member.id}>
              <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <CardTitle>{member.fullName}</CardTitle>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{member.role}</Badge>
                    <Badge className="border-primary/30 bg-primary/15 text-primary">{member.persona}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <label className="space-y-2 text-sm">
                    <span className="text-muted-foreground">Role</span>
                    <select
                      className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary"
                      value={draft.role}
                      onChange={(event) => updateDraft(member.id, { role: event.target.value as Role })}
                    >
                      {ROLE_OPTIONS.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-2 text-sm">
                    <span className="text-muted-foreground">Persona</span>
                    <select
                      className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary"
                      value={draft.persona}
                      onChange={(event) => updateDraft(member.id, { persona: event.target.value as Persona })}
                    >
                      {personaOptions(orgType).map((persona) => (
                        <option key={persona} value={persona}>
                          {persona}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-2 text-sm">
                    <span className="text-muted-foreground">Designation</span>
                    <Input
                      value={draft.designation}
                      onChange={(event) => updateDraft(member.id, { designation: event.target.value })}
                    />
                  </label>
                </div>
                <div className="flex gap-3">
                  <Button
                    type="button"
                    disabled={!dirty || pendingId === member.id}
                    onClick={() => void saveMember(member)}
                  >
                    {pendingId === member.id ? "Saving..." : "Save member"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={!dirty || pendingId === member.id}
                    onClick={() => resetDraft(member)}
                  >
                    Reset
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
