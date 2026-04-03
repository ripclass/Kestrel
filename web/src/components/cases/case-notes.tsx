"use client";

import { useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { CaseNote } from "@/types/domain";

export function CaseNotes({
  notes,
  isSubmitting,
  onAddNote,
}: {
  notes: CaseNote[];
  isSubmitting: boolean;
  onAddNote: (note: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState("");

  async function submitNote() {
    const note = draft.trim();
    if (!note) {
      return;
    }
    await onAddNote(note);
    setDraft("");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3 text-sm text-muted-foreground">
          {notes.length === 0 ? <p>No case notes yet.</p> : null}
          {notes.map((note) => (
            <div key={`${note.occurredAt}-${note.note}`} className="rounded-xl border border-border/70 bg-background/50 p-4">
              <div className="flex items-center justify-between gap-4">
                <p className="font-medium text-foreground">{note.actorUserId}</p>
                <span className="text-xs uppercase tracking-[0.16em]">{note.actorRole}</span>
              </div>
              <p className="mt-2">{note.note}</p>
              <p className="mt-2 text-xs">{new Date(note.occurredAt).toLocaleString()}</p>
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Add note</label>
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Record analyst reasoning, requested documents, or next investigative steps."
          />
        </div>
        <Button type="button" disabled={isSubmitting || !draft.trim()} onClick={() => void submitNote()}>
          {isSubmitting ? "Saving note..." : "Add note"}
        </Button>
      </CardContent>
    </Card>
  );
}
