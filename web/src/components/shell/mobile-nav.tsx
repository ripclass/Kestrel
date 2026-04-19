"use client";

import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";

import { SidebarNav } from "@/components/shell/sidebar-nav";
import { cn } from "@/lib/utils";
import type { Viewer } from "@/types/domain";

/**
 * Mobile-only navigation. Hidden at lg+ where the desktop AppSidebar
 * takes over. The trigger button is a fixed top-left tile that aligns
 * with the topbar height; the drawer slides in from the left and
 * mirrors the SidebarNav contents. Closes on backdrop click, Escape
 * key, or any nav link click (via the SidebarNav onNavigate callback).
 */
export function MobileNav({ viewer }: { viewer: Viewer }) {
  const [open, setOpen] = useState(false);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // Lock body scroll while the drawer is open.
  useEffect(() => {
    if (!open) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        aria-label={open ? "Close navigation" : "Open navigation"}
        aria-expanded={open}
        aria-controls="mobile-nav-drawer"
        onClick={() => setOpen((prev) => !prev)}
        className="fixed left-3 top-3 z-40 inline-flex h-10 w-10 items-center justify-center border border-border bg-card text-foreground transition hover:border-foreground lg:hidden"
      >
        {open ? (
          <X aria-hidden="true" className="h-4 w-4" />
        ) : (
          <Menu aria-hidden="true" className="h-4 w-4" />
        )}
      </button>

      {/* Backdrop. Mounted only when open so it doesn't intercept taps
          on closed state. */}
      {open ? (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
        />
      ) : null}

      {/* Drawer. Always mounted so the SidebarNav fetch runs once and
          the slide-in transition has something to animate from. */}
      <div
        id="mobile-nav-drawer"
        role="dialog"
        aria-label="Primary navigation"
        aria-hidden={!open}
        className={cn(
          "fixed left-0 top-0 z-30 h-full w-72 max-w-[85vw] border-r border-[var(--sidebar-border)] bg-[var(--sidebar)] text-[var(--sidebar-foreground)] transition-transform duration-200 ease-out lg:hidden",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <SidebarNav viewer={viewer} onNavigate={() => setOpen(false)} />
      </div>
    </>
  );
}
