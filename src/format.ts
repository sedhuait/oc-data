import { readFileSync, writeFileSync } from "node:fs";
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

export function formatAll(check: boolean): string[] {
  const dirty: string[] = [];
  for (const file of productFiles()) {
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
  const dirty = formatAll(check);
  if (check && dirty.length) {
    console.log("These files are not canonically formatted. Run: npm run format");
    for (const d of dirty) console.log("  " + d);
    process.exit(1);
  }
  console.log(`${check ? "would reformat" : "formatted"} ${dirty.length} files`);
}
