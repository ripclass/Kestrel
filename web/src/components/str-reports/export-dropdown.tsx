"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

type ExportOption = {
  label: string;
  href: string;
  hint?: string;
};

export function ExportDropdown({
  options,
  triggerLabel = "Export",
}: {
  options: ExportOption[];
  triggerLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(event: MouseEvent) {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("mousedown", onClickOutside);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onClickOutside);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative inline-block">
      <Button type="button" variant="outline" onClick={() => setOpen((prev) => !prev)}>
        {triggerLabel} ▾
      </Button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-10 mt-2 w-64 overflow-hidden rounded-xl border border-border bg-card shadow-lg"
        >
          {options.map((option) => (
            <a
              key={option.href}
              href={option.href}
              className="block px-4 py-2 text-sm transition hover:bg-background/60"
              onClick={() => setOpen(false)}
            >
              <div className="font-medium">{option.label}</div>
              {option.hint ? <div className="text-xs text-muted-foreground">{option.hint}</div> : null}
            </a>
          ))}
        </div>
      ) : null}
    </div>
  );
}
