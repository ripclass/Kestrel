"use client";

import { useState } from "react";

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
    if (!note) return;
    await onAddNote(note);
    setDraft("");
  }

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Case notes
        </p>
      </div>
      <div className="space-y-6 p-6">
        {notes.length === 0 ? (
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            No case notes yet
          </p>
        ) : (
          <ul className="divide-y divide-border border border-border">
            {notes.map((note) => (
              <li key={`${note.occurredAt}-${note.note}`} className="space-y-2 px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-mono text-sm text-foreground">{note.actorUserId}</p>
                  <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                    {note.actorRole}
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-foreground">{note.note}</p>
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  {new Date(note.occurredAt).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        )}
        <div className="space-y-3">
          <label className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Add note
          </label>
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Record analyst reasoning, requested documents, or next investigative steps."
          />
          <Button type="button" disabled={isSubmitting || !draft.trim()} onClick={() => void submitNote()}>
            {isSubmitting ? "Saving note…" : "Add note"}
          </Button>
        </div>
      </div>
    </section>
  );
}
