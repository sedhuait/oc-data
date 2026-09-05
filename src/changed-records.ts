/**
 * Print the records that changed between two git refs, as NDJSON — the
 * exact body /ingest expects (HLD §15.1: publish the diff, not the
 * catalogue). A one-line fix should POST one record, not 24,000.
 *
 * Usage: node src/changed-records.ts <base-sha> <head-sha>
 *
 * Removed records are deliberately NOT emitted here: /ingest only
 * upserts, it has no delete, and a removal needs a person's judgement
 * (see diff-summary.ts, which does surface removals for the PR body).
 */
import { execFileSync } from "node:child_process";
import type { ProductRecord } from "./schema.ts";

const git = (...args: string[]) =>
  execFileSync("git", args, { encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });

function load(ref: string): Map<string, ProductRecord> {
  const out = new Map<string, ProductRecord>();
  let files: string[] = [];
  try {
    files = git("ls-tree", "-r", "--name-only", ref, "products/")
      .split("\n")
      .filter((f) => f.endsWith(".jsonl"));
  } catch {
    return out; // ref doesn't exist yet (e.g. first commit, or a shallow/empty base)
  }
  for (const f of files) {
    let text: string;
    try {
      text = git("show", `${ref}:${f}`);
    } catch {
      continue; // file existed in the tree listing but not at this exact ref — skip
    }
    for (const line of text.split("\n")) {
      if (!line.trim()) continue;
      const r = JSON.parse(line) as ProductRecord;
      out.set(r.id, r);
    }
  }
  return out;
}

const [base, head] = process.argv.slice(2);
if (!base || !head) {
  console.error("usage: node src/changed-records.ts <base-sha> <head-sha>");
  process.exit(1);
}

// `git push --force` or a repo's very first push leaves `before` as the
// all-zeros SHA GitHub uses for "no previous commit" — there is nothing to
// diff against, so treat it as "everything is new" rather than failing.
const ZERO_SHA = "0000000000000000000000000000000000000000";
const a = base === ZERO_SHA ? new Map<string, ProductRecord>() : load(base);
const b = load(head);

const changed: ProductRecord[] = [];
for (const [id, after] of b) {
  const before = a.get(id);
  if (!before || JSON.stringify(before, Object.keys(before).sort()) !== JSON.stringify(after, Object.keys(after).sort())) {
    changed.push(after);
  }
}

for (const record of changed) {
  process.stdout.write(JSON.stringify(record) + "\n");
}
console.error(`${changed.length} record(s) changed out of ${b.size} total`);
