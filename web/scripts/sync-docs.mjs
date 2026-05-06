// Copies the four public-facing documentation files from /docs/ at the repo
// root into web/src/content/docs/ at build time. The .md files at the repo
// root remain the source of truth; the web bundle gets its own copy so the
// Vercel build doesn't have to reach outside the web/ root.
//
// Run via the `prebuild` lifecycle hook in package.json, and locally before
// `next dev` if you've just edited one of the source docs.

import { mkdir, copyFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..", "..");
const sourceDir = join(repoRoot, "docs");
const targetDir = join(__dirname, "..", "src", "content", "docs");

const docs = [
  "cross-bank-intelligence.md",
  "goaml-coverage.md",
  "world-class-capability-matrix.md",
  "multi-tenant-isolation-verified.md",
];

async function main() {
  await mkdir(targetDir, { recursive: true });
  for (const name of docs) {
    const src = join(sourceDir, name);
    const dst = join(targetDir, name);
    await copyFile(src, dst);
    console.log(`synced ${name}`);
  }
}

main().catch((err) => {
  console.error("doc sync failed:", err);
  process.exit(1);
});
