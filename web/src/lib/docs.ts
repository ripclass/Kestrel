import { readFile } from "node:fs/promises";
import { join } from "node:path";

const DOC_ROOT = join(process.cwd(), "src", "content", "docs");

export type DocSlug =
  | "cross-bank-intelligence"
  | "goaml-coverage"
  | "world-class-capability-matrix"
  | "multi-tenant-isolation-verified";

// Read a synced markdown doc from web/src/content/docs/.
// Strips the first H1 and any leading bold metadata lines so the page hero
// can render its own (designed) title block. Returns the remaining body.
export async function readDocBody(slug: DocSlug): Promise<string> {
  const raw = await readFile(join(DOC_ROOT, `${slug}.md`), "utf8");
  const lines = raw.split("\n");
  let i = 0;
  // skip leading blank lines
  while (i < lines.length && lines[i].trim() === "") i++;
  // skip the first H1
  if (i < lines.length && /^#\s/.test(lines[i])) i++;
  // skip leading metadata: blank lines + bold lines + blockquote intro lines
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (trimmed === "") {
      i++;
      continue;
    }
    if (trimmed.startsWith("**") && trimmed.endsWith("**")) {
      i++;
      continue;
    }
    if (trimmed.startsWith("_") && trimmed.endsWith("_")) {
      i++;
      continue;
    }
    if (trimmed.startsWith(">")) {
      i++;
      continue;
    }
    break;
  }
  // skip any --- horizontal rule that follows the metadata
  while (i < lines.length && (lines[i].trim() === "" || lines[i].trim() === "---")) {
    i++;
  }
  return lines.slice(i).join("\n");
}
