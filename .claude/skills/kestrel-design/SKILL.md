# Kestrel Landing Page Style Guide: Sovereign Ledger

## Design Posture
**Institutional Brutalism / Sovereign Ledger.** 
Weaponized ledger-and-dossier aesthetic. Precision-instrument posture. This is the public face of a central bank's intelligence vault—not a startup SaaS product. Absolute, unvarnished authority. 

## Color Palette (Landing Page Only)
The landing page operates on a distinct set of tokens, separating it from the in-app interface.

| Token Name | Hex / RGBA | Purpose |
|---|---|---|
| `--landing-bg` | `#0F1115` | Deep slate/charcoal. The baseline dark void for all surfaces. |
| `--landing-foreground` | `#EAE6DA` | Bone white. Primary text for all copy. Cold, print-like. |
| `--landing-alarm` | `#FF3823` | Fluorescent Vermillion. Used **only** for anomaly, flagged nodes, and the critical CTAs. It is not an accent; it is an alarm state. |
| `--landing-rule` | `rgba(234, 230, 218, 0.08)` | Hairline wireframing. The structural grid over the void. |
| `--landing-rule-solid` | `#2A2C30` | Solid borders for input fields and discrete bounds. |
| `--landing-muted` | `#8E929A` | Neutral grey for metadata, timestamps, and secondary text. |

*Strict Rules:* No teal. No blue. No gradients. No glow.

## Typography
Use monospace exclusively. No humanist sans-serif.

| Usage | Primary (Licensed) | Fallback (Google Fonts) | Characteristics |
|---|---|---|---|
| **Display** | GT Alpina Mono (Klim) | `IBM Plex Mono` | Rigid, sharp, printed feel. Used for H1/H2 and hero values. |
| **Body** | Söhne Mono (Klim) | `JetBrains Mono` | Machine-level precision, dense data reading, highly auditable. |

*Note for Implementation:* The fallback fonts are currently integrated into the `layout.tsx` file using `next/font/google`. When licensing the Klim fonts, swap the root CSS variables in `globals.css` via local `@font-face` declarations.

## Composition & Grid Rules
- **Strict Swiss Grid:** Maintain rigid columns.
- **Visible Wireframes:** Expose the structure (`border-landing-rule`) instead of standard padding limits.
- **Alignment:** Strongly left-aligned. No centered text sections.
- **Negative Space:** Dense data panels must be balanced against massive void space.

## The Signature Device: The Registration Crosshair (`┼`)
Treat the `┼` as Kestrel's typographic glyph. It metaphorizes "locking onto a target" and "auditability."
- **Dos:** Place at exact grid intersections of the Hero, the corners of intake forms, or flagging a single node in a graph.
- **Don'ts:** Do not use it as a bullet point. Do not scatter it randomly. It loses power if overused.

## Component Recipes

### The Hero / Full-Bleed Network
The hero is not a marketing block; it is an edge-to-edge terminal view.
1. Wrap the entire view in `bg-landing-bg border-b border-landing-rule`.
2. Map out a dense, massive SVG node network.
3. Call out specific anomalous nodes using `--landing-alarm` and `┼`.
4. Run 1px rules from the nodes horizontally out to the edges.

### The Intake Form
A severely styled "Request Clearance" form. No mailtos. 
- **Fields:** Hard-edged rectangles using `border-landing-rule-solid` on focus `border-landing-foreground`. 
- **Typography:** Placeholder text should look like a terminal prompt.
- **Submit Button:** Left-aligned, `bg-landing-alarm text-landing-bg`. Pure brutalism.

### Stats Strip
A horizontal ledger `flex-row border-y border-landing-rule divide-x divide-landing-rule`. Raw numbers in Display Mono, labels in Body Mono uppercase.
