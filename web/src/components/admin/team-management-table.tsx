"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
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
  if (orgType === "regulator") return ["bfiu_analyst", "bfiu_director"];
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

const selectClass =
  "h-11 w-full rounded-none border border-input bg-card px-4 text-sm outline-none focus:border-foreground";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
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
    setDrafts((current) => ({ ...current, [memberId]: { ...current[memberId], ...patch } }));
  }

  function resetDraft(member: AdminTeamMember) {
    setDrafts((current) => ({ ...current, [member.id]: toDraft(member) }));
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
    setMembers((current) =>
      current.map((entry) => (entry.id === updatedMember.id ? updatedMember : entry)),
    );
    setDrafts((current) => ({ ...current, [updatedMember.id]: toDraft(updatedMember) }));
    setNotice(`${updatedMember.fullName} updated.`);
    setPendingId(null);
  }

  return (
    <div className="space-y-4">
      {notice ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
          <span aria-hidden className="mr-2">┼</span>
          {notice}
        </p>
      ) : null}
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          <span aria-hidden className="mr-2">┼</span>ERROR · {error}
        </p>
      ) : null}
      <div className="grid gap-4">
        {members.map((member) => {
          const draft = drafts[member.id];
          const dirty = !sameDraft(draft, toDraft(member));

          return (
            <section key={member.id} className="border border-border">
              <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                    <span aria-hidden className="mr-2 text-accent">┼</span>
                    Operator · {member.fullName}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <span className="border border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-foreground">
                      {member.role}
                    </span>
                    <span className="border border-accent/40 bg-accent/10 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-accent">
                      {member.persona}
                    </span>
                  </div>
                </div>
              </div>
              <div className="space-y-5 p-6">
                <div className="grid gap-4 md:grid-cols-3">
                  <Field label="Role">
                    <select
                      className={selectClass}
                      value={draft.role}
                      onChange={(event) =>
                        updateDraft(member.id, { role: event.target.value as Role })
                      }
                    >
                      {ROLE_OPTIONS.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Persona">
                    <select
                      className={selectClass}
                      value={draft.persona}
                      onChange={(event) =>
                        updateDraft(member.id, { persona: event.target.value as Persona })
                      }
                    >
                      {personaOptions(orgType).map((persona) => (
                        <option key={persona} value={persona}>
                          {persona}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Designation">
                    <Input
                      value={draft.designation}
                      onChange={(event) => updateDraft(member.id, { designation: event.target.value })}
                    />
                  </Field>
                </div>
                <div className="flex gap-2 border-t border-border pt-4">
                  <Button
                    type="button"
                    disabled={!dirty || pendingId === member.id}
                    onClick={() => void saveMember(member)}
                  >
                    {pendingId === member.id ? "Saving…" : "Save member"}
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
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
