import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { productFiles, readRecords, rel, type ProductRecord } from "./schema.ts";

/** Drop empty values so diffs stay small, but keep the shape containers. */
export function clean(r: ProductRecord): Record<string, unknown> {
  const KEEP = new Set(["attributes", "identifiers", "urls"]);
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(r)) {
    const empty = v === null || v === undefined || v === "" ||
      (Array.isArray(v) && v.length === 0) ||
      (typeof v === "object" && !Array.isArray(v) && Object.keys(v as object).length === 0);
    if (empty && !KEEP.has(k)) continue;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      const inner = Object.fromEntries(Object.entries(v as object).filter(([, vv]) => vv !== "" && !(Array.isArray(vv) && vv.length === 0)));
      out[k] = inner;
    } else out[k] = v;
  }
  return out;
}

/** Recursively sort object keys. NEVER use JSON.stringify's replacer-array for this:
 *  it filters keys at every nesting level, which silently empties nested objects. */
export function sortKeysDeep(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(sortKeysDeep);
  if (v && typeof v === "object") {
    const o = v as Record<string, unknown>;
    return Object.fromEntries(Object.keys(o).sort().map((k) => [k, sortKeysDeep(o[k])]));
  }
  return v;
}

/** Keys sorted, one object per line, lines sorted by (category, name, id). */
export function render(records: ProductRecord[]): string {
  const sorted = [...records].sort((a, b) =>
    (a.category ?? "").localeCompare(b.category ?? "") ||
    (a.name ?? "").toLowerCase().localeCompare((b.name ?? "").toLowerCase()) ||
    (a.id ?? "").localeCompare(b.id ?? ""));
  return sorted.map((r) => JSON.stringify(sortKeysDeep(clean(r))) + "\n").join("");
}

export function formatAll(check: boolean, only?: string[]): string[] {
  const dirty: string[] = [];
  // `only` narrows the walk to paths under the given prefixes. Several
  // crawlers write to this tree at once, and a repo-wide rewrite launched
  // while another process is mid-write has cost records here: one run left
  // 14 files at zero bytes and dropped 36 grocery records. Formatting your
  // own domain should not require touching anybody else's.
  const prefixes = (only ?? []).map((p) => resolve(p));
  const wanted = (file: string) =>
    prefixes.length === 0 || prefixes.some((p) => file === p || file.startsWith(p + "/"));
  for (const file of productFiles()) {
    if (!wanted(file)) continue;
    const records: ProductRecord[] = [];
    for (const item of readRecords(file)) if ("record" in item) records.push(item.record);
    const body = render(records);
    if (readFileSync(file, "utf8") !== body) {
      dirty.push(rel(file));
      if (!check) writeFileSync(file, body);
    }
  }
  return dirty;
}

if (import.meta.filename === process.argv[1]) {
  const check = process.argv.includes("--check");
  const only = process.argv.slice(2).filter((a) => !a.startsWith("--"));
  const dirty = formatAll(check, only);
  if (check && dirty.length) {
    console.log("These files are not canonically formatted. Run: npm run format");
    for (const d of dirty) console.log("  " + d);
    process.exit(1);
  }
  console.log(`${check ? "would reformat" : "formatted"} ${dirty.length} files`);
}
