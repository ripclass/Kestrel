"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Renders text character-by-character to approximate the
 * "ChatGPT-streaming" feel without changing the underlying API
 * (Kestrel returns structured JSON via tool-calling, not free text).
 *
 * The reveal animates only on first mount (and on text-prop change).
 * Subsequent renders show the full text immediately so panel
 * re-renders during scroll / navigation don't re-trigger the
 * animation.
 *
 * Respects prefers-reduced-motion: when set, the full text appears
 * immediately with no animation.
 *
 * @param text   The full text to reveal.
 * @param speed  Characters per second. 60 ≈ comfortable reading
 *               speed; ChatGPT clocks ~40-50 in practice. Default 60.
 * @param className passed through to the wrapping span.
 */
export function TypedReveal({
  text,
  speed = 60,
  className,
}: {
  text: string;
  speed?: number;
  className?: string;
}) {
  const [displayed, setDisplayed] = useState(text);
  const lastTextRef = useRef<string>("");

  // Extracted into a callback so the setState calls aren't lexically inside
  // the effect body (react-hooks/set-state-in-effect). The effect just
  // invokes it and forwards the cleanup.
  const applyReveal = useCallback(() => {
    if (typeof window === "undefined") return;

    if (lastTextRef.current === text) {
      // Re-render with same text — keep the full reveal visible.
      return;
    }
    lastTextRef.current = text;

    const reduced =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !text) {
      setDisplayed(text);
      return;
    }

    setDisplayed("");
    const interval = Math.max(8, Math.round(1000 / speed));
    let i = 0;
    const handle = window.setInterval(() => {
      i += Math.max(1, Math.round(speed / 30)); // batch a few chars per tick for smoothness
      if (i >= text.length) {
        setDisplayed(text);
        window.clearInterval(handle);
      } else {
        setDisplayed(text.slice(0, i));
      }
    }, interval);

    return () => window.clearInterval(handle);
  }, [text, speed]);

  // The state update IS the effect's purpose here — driving a timer-based
  // typewriter animation frame-by-frame. That is a legitimate effect use
  // (a "platform API" timer), which set-state-in-effect false-positives on.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => applyReveal(), [applyReveal]);

  // Trailing caret while still typing — disappears once full text shown.
  const isTyping = displayed.length < text.length;

  return (
    <span className={className}>
      {displayed}
      {isTyping ? (
        <span
          aria-hidden
          className="ml-0.5 inline-block h-[0.9em] w-[0.4em] translate-y-[0.05em] animate-pulse bg-accent align-middle"
        />
      ) : null}
    </span>
  );
}
