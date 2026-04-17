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
          className="absolute right-0 z-10 mt-2 w-72 divide-y divide-border border border-border bg-card"
        >
          {options.map((option) => (
            <a
              key={option.href}
              href={option.href}
              className="block px-4 py-3 transition hover:bg-foreground/[0.03]"
              onClick={() => setOpen(false)}
            >
              <div className="text-sm font-medium text-foreground">{option.label}</div>
              {option.hint ? (
                <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  {option.hint}
                </div>
              ) : null}
            </a>
          ))}
        </div>
      ) : null}
    </div>
  );
}
