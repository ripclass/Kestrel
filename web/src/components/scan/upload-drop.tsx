"use client";

import { useRef } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function UploadDrop({
  fileName,
  file,
  onFileNameChange,
  onFileChange,
}: {
  fileName: string;
  file: File | null;
  onFileNameChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    onFileChange(selected);
    if (selected) onFileNameChange(selected.name);
  }

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Upload transactions
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Drop a CSV export to run detection on just those transactions. Expected columns: posted_at,
          src_account, amount. Optional: dst_account, currency, channel, tx_type, description.
        </p>
      </div>
      <div className="space-y-5 p-6">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="block w-full border border-dashed border-border bg-card/50 px-6 py-12 text-center font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition hover:border-foreground hover:bg-foreground/[0.03]"
        >
          {file ? (
            <>
              <span className="block text-sm text-accent">{file.name}</span>
              <span className="mt-1 inline-block text-[10px]">
                {(file.size / 1024).toFixed(1)} KB · click to replace
              </span>
            </>
          ) : (
            <>
              <span className="block">Click to choose a CSV, or leave empty to scan the existing database</span>
              <span className="mt-1 inline-block text-[10px] text-muted-foreground/70">
                (drag &amp; drop support in a later cut)
              </span>
            </>
          )}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={handleFileSelected}
        />
        {file ? (
          <Button type="button" variant="outline" onClick={() => onFileChange(null)}>
            Remove file
          </Button>
        ) : null}
        <div className="space-y-2">
          <label className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Source file label
          </label>
          <Input
            value={fileName}
            onChange={(event) => onFileNameChange(event.target.value)}
            placeholder="dbbl-wallet-burst-apr03.csv"
          />
        </div>
      </div>
    </section>
  );
}
