"use client";

import { useRef } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
    if (selected) {
      onFileNameChange(selected.name);
    }
  }

  return (
    <Card className="grid-surface">
      <CardHeader>
        <CardTitle>Upload transactions</CardTitle>
        <CardDescription>
          Drop a CSV export to run detection on just those transactions. Expected columns:
          posted_at, src_account, amount. Optional: dst_account, currency, channel, tx_type, description.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="block w-full rounded-2xl border border-dashed border-primary/40 bg-background/40 px-6 py-12 text-center text-sm text-muted-foreground transition hover:border-primary/60 hover:bg-background/60"
        >
          {file ? (
            <>
              <span className="block font-medium text-primary">{file.name}</span>
              <span className="text-xs">{(file.size / 1024).toFixed(1)} KB · click to replace</span>
            </>
          ) : (
            <>
              <span className="block">Click to choose a CSV, or leave empty to scan the existing database.</span>
              <span className="text-xs">(Drag &amp; drop support in a later cut.)</span>
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
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Button type="button" variant="outline" onClick={() => onFileChange(null)}>
              Remove file
            </Button>
          </div>
        ) : null}
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-primary">Source file label</p>
          <Input
            value={fileName}
            onChange={(event) => onFileNameChange(event.target.value)}
            placeholder="dbbl-wallet-burst-apr03.csv"
          />
        </div>
      </CardContent>
    </Card>
  );
}
