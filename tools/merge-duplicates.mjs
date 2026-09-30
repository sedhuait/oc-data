// Merges records that describe the same product: same brand, same name,
// same pack (the validator's W2 key). Dry run by default.
//
//   node tools/merge-duplicates.mjs            # report what would merge
//   node tools/merge-duplicates.mjs --apply    # write
//
// A merge happens only when the records AGREE: no attribute present on both
// with different values. Agreeing records lose nothing by merging — the kept
// record (most facts; then a brand's own source; then lowest id) gains any
// fact it lacks and every source the other cites, so provenance survives. The
// other record stays in the file with `superseded_by`, which is how this repo
// retires a record without deleting its history.
//
// Records that DISAGREE are left alone and listed: either they are different
// products the name doesn't separate, or one of them is wrong — a person has
// to decide which, and a merge would quietly pick a side.
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = join(import.meta.dirname, "..", "products");
const APPLY = process.argv.includes("--apply");
const norm = (s) => String(s ?? "").normalize("NFKD").toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b) || (typeof a === "string" && typeof b === "string" && norm(a) === norm(b));
const RANK = { "brand-store": 0, "brand-submitted": 1, manual: 2, "marketplace-api": 3, "marketplace-feed": 4, extension: 5, ocr: 6 };

// load every record with its location
const files = new Map(); // path -> array of lines (parsed or raw)
const all = [];
for (const d of readdirSync(ROOT)) {
  for (const f of readdirSync(join(ROOT, d)).filter((x) => x.endsWith(".jsonl"))) {
    const p = join(ROOT, d, f);
    const lines = readFileSync(p, "utf8").split("\n");
    files.set(p, lines);
    lines.forEach((line, i) => {
      if (!line.trim()) return;
      all.push({ r: JSON.parse(line), file: p, i });
    });
  }
}

// Two passes, each a way of knowing two records are one product:
//  1. same brand, name and pack (the validator's W2 key)
//  2. same barcode and same pack — a GTIN names one product in one pack, so
//     this catches "Dove" vs "Hindustan Unilever" spellings of the same item.
//     A shared barcode with a DIFFERENT pack means one barcode is wrong; those
//     are not merged.
const packOf = (r) => norm(String(r.size ?? r.attributes?.quantity ?? "")).replace(/\s/g, "");
const PASSES = [
  (r) => `${norm(r.brand)}|${norm(r.name)}|${norm(r.size ?? r.attributes?.quantity ?? "")}`,
  (r) => (r.identifiers?.gtin ? `${r.identifiers.gtin}|${packOf(r)}` : null),
];

const facts = (r) => Object.keys(r.attributes ?? {}).length + (r.ingredients?.length ? 1 : 0);
const bestSource = (r) => Math.min(...r.sources.map((s) => RANK[s.kind] ?? 9));

// Free text that names who made or sells a product, written differently by
// different retailers ("Hindustan Unilever Ltd, Mumbai" vs "HUL, Andheri…").
// A difference here says nothing about whether it's the same product.
const SOFT = new Set(["manufacturer", "marketed_by", "country_of_origin", "storage_instructions", "packaging_type", "fssai_licence"]);

// The Blinkit grocery crawl filed personal-care products under grocery
// catch-alls — measured 2026-09-30: ~350 shampoos, face washes, moisturisers
// and fragrances sat in "Staples & grains". Where the same product also has a
// beauty record, that record is in the right place and is the one kept.
const GROCERY_CATCHALL = new Set(["Staples & grains", "Oils & ghee", "_default"]);
// Open Beauty Facts imports land in one bucket until someone files them.
const BEAUTY_CATCHALL = new Set(["Beauty (Open Beauty Facts)", "_default"]);
const catchAll = (r) =>
  (r.domain === "grocery" && GROCERY_CATCHALL.has(r.category)) || (r.domain === "beauty" && BEAUTY_CATCHALL.has(r.category));
// `a` is the better-filed twin of `b`: b sits in a catch-all and a doesn't,
// with a beauty record beating a grocery one filed as staples.
const misfiledTwin = (a, b) =>
  catchAll(b) && !catchAll(a) && (a.domain === b.domain || (a.domain === "beauty" && b.domain === "grocery"));

const schemaFields = new Map();
const fieldsOf = (domain) => {
  if (!schemaFields.has(domain)) {
    const s = JSON.parse(readFileSync(join(ROOT, "..", "schemas", `${domain}.json`), "utf8"));
    schemaFields.set(domain, new Set(Object.keys(s.fields ?? {})));
  }
  return schemaFields.get(domain);
};
let merged = 0;
const conflicts = [];
const changed = new Set();
const byDomain = {};

for (const keyOf of PASSES) {
const groups = new Map();
for (const x of all) {
  if (x.r.superseded_by) continue; // includes records retired by the pass before
  const key = keyOf(x.r);
  if (key === null) continue;
  if (!groups.has(key)) groups.set(key, []);
  groups.get(key).push(x);
}
for (const group of groups.values()) {
  if (group.length < 2) continue;
  // a beauty record beats its grocery-catch-all twin; otherwise most facts wins
  group.sort(
    (a, b) =>
      (misfiledTwin(b.r, a.r) ? 1 : 0) - (misfiledTwin(a.r, b.r) ? 1 : 0) ||
      facts(b.r) - facts(a.r) ||
      bestSource(a.r) - bestSource(b.r) ||
      a.r.id.localeCompare(b.r.id),
  );
  const keep = group[0];
  for (const other of group.slice(1)) {
    const a = keep.r.attributes ?? {};
    const b = other.r.attributes ?? {};
    const clash = Object.keys(b).filter(
      (k) => !SOFT.has(k) && k in a && a[k] !== null && b[k] !== null && !same(a[k], b[k]),
    );
    if (keep.r.category !== other.r.category && !misfiledTwin(keep.r, other.r)) clash.push("category");
    if (clash.length) {
      conflicts.push(`${relative(ROOT, other.file)}:${other.i + 1} ${other.r.brand} · ${other.r.name.slice(0, 50)} — disagrees with ${keep.r.id} on ${clash.slice(0, 4).join(", ")}`);
      continue;
    }
    // fill what the kept record lacks, only with fields its own schema
    // defines; never overwrite a value it already has
    const allowed = fieldsOf(keep.r.domain);
    keep.r.attributes = { ...a };
    for (const k of Object.keys(b)) {
      if (allowed.has(k) && (a[k] === null || a[k] === undefined)) keep.r.attributes[k] = b[k];
    }
    if (!keep.r.ingredients?.length && other.r.ingredients?.length) keep.r.ingredients = other.r.ingredients;
    if (!keep.r.images?.length && other.r.images?.length) keep.r.images = other.r.images;
    for (const [k, v] of Object.entries(other.r.identifiers ?? {})) {
      keep.r.identifiers ??= {};
      if (v && !keep.r.identifiers[k]) keep.r.identifiers[k] = v;
    }
    const seen = new Set(keep.r.sources.map((s) => `${s.kind}|${s.url ?? ""}`));
    for (const s of other.r.sources) if (!seen.has(`${s.kind}|${s.url ?? ""}`)) keep.r.sources.push(s);
    other.r.superseded_by = keep.r.id;
    merged++;
    const dom = relative(ROOT, other.file).split("/")[0];
    byDomain[dom] = (byDomain[dom] ?? 0) + 1;
    for (const x of [keep, other]) {
      files.get(x.file)[x.i] = JSON.stringify(x.r);
      changed.add(x.file);
    }
  }
}
}

console.log(`${merged} duplicate records merged into the record they repeat (${JSON.stringify(byDomain)})`);
console.log(`${conflicts.length} left alone because the two records disagree:`);
for (const c of conflicts.slice(0, 12)) console.log(`   ${c}`);
if (conflicts.length > 12) console.log(`   … ${conflicts.length - 12} more`);
if (!APPLY) {
  console.log("\ndry run — re-run with --apply to write, then: npm run format && npm run validate");
} else {
  for (const f of changed) writeFileSync(f, files.get(f).join("\n"));
  console.log(`\nwrote ${changed.size} file(s). Now: npm run format && npm run validate`);
}
