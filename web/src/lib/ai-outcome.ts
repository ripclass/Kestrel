/**
 * AI outcome-correction capture (V3 sovereign-LLM training corpus).
 *
 * Every AI invocation returns an `ai_outcome_log` row id in its `meta`.
 * When an analyst acts on that AI output — edits a drafted STR narrative,
 * accepts or rejects an alert explanation — the verdict is posted back here.
 * Rows with an `analyst_correction` become the gold training corpus the
 * sovereign model fine-tunes on.
 *
 * This is best-effort: capturing the training signal must never break or
 * block the analyst's actual action, so failures are swallowed.
 */

export type AiOutcomeLabel =
  | "true_positive"
  | "false_positive"
  | "accepted"
  | "rejected"
  | "edited";

export async function recordAiCorrection(
  logId: string | null | undefined,
  body: { correction?: Record<string, unknown>; outcomeLabel?: AiOutcomeLabel },
): Promise<void> {
  if (!logId) {
    return;
  }
  try {
    await fetch(`/api/ai/outcomes/${encodeURIComponent(logId)}/correction`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        correction: body.correction,
        outcome_label: body.outcomeLabel,
      }),
    });
  } catch {
    // Best-effort — never let training-signal capture surface to the user.
  }
}
