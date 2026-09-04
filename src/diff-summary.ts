import { execFileSync } from "node:child_process";
import type { ProductRecord } from "./schema.ts";

const git = (...args: string[]) => execFileSync("git", args, { encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });

function load(ref: string): Map<string, ProductRecord> {
  const out = new Map<string, ProductRecord>();
  let files: string[] = [];
  try { files = git("ls-tree", "-r", "--name-only", ref, "products/").split("\n").filter((f) => f.endsWith(".jsonl")); }
  catch { return out; }
  for (const f of files) {
    for (const line of git("show", `${ref}:${f}`).split("\n")) {
      if (!line.trim()) continue;
      const r = JSON.parse(line) as ProductRecord;
      out.set(r.id, r);
    }
  }
  return out;
}

const [base, head] = process.argv.slice(2);
const a = load(base), b = load(head);

const added = [...b.keys()].filter((k) => !a.has(k)).map((k) => b.get(k)!);
const removed = [...a.keys()].filter((k) => !b.has(k)).map((k) => a.get(k)!);
const changed: Array<{ r: ProductRecord; fields: string[] }> = [];
for (const id of b.keys()) {
  if (!a.has(id)) continue;
  const before = a.get(id)!, after = b.get(id)!;
  const fields = [...new Set([...Object.keys(before), ...Object.keys(after)])]
    .filter((k) => JSON.stringify((before as never)[k]) !== JSON.stringify((after as never)[k])).sort();
  if (fields.length) changed.push({ r: after, fields });
}

const lines: string[] = ["## What this changes", "",
  `**${added.length} added · ${changed.length} updated · ${removed.length} removed**`, ""];

if (added.length) {
  const by = new Map<string, number>();
  for (const r of added) { const k = `${r.brand} — ${r.category}`; by.set(k, (by.get(k) ?? 0) + 1); }
  lines.push("### Added");
  for (const [k, n] of [...by].sort((x, y) => y[1] - x[1]).slice(0, 12)) lines.push(`- ${k}: ${n}`);
  lines.push("");
}
if (changed.length) {
  lines.push("### Updated");
  for (const { r, fields } of changed.slice(0, 20)) lines.push(`- ${r.brand} — ${r.name.slice(0, 60)}: ${fields.join(", ")}`);
  if (changed.length > 20) lines.push(`- …and ${changed.length - 20} more`);
  lines.push("");
}
if (removed.length) {
  lines.push("### Removed — a maintainer needs to confirm each of these");
  for (const r of removed.slice(0, 20)) lines.push(`- ${r.brand} — ${r.name.slice(0, 60)} (\`${r.id}\`)`);
  lines.push("");
}
const ing = changed.filter((c) => c.fields.includes("ingredients"));
if (ing.length) lines.push(`> ${ing.length} ingredient lists changed. Ingredients are the fact people trust most — each needs a source URL or a photo of the pack.`, "");

console.log(lines.join("\n"));
