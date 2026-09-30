import {
  ROOT, TOP_LEVEL_FIELDS, brandFileFor, gtinValid, loadDomainSchemas, norm,
  productFiles, readRecords, rel, IDENTIFIER_KEYS,
  type AttrValue, type DomainSchema, type FieldSpec, type ProductRecord,
} from "./schema.ts";

export interface Finding { file: string; line: number; code: string; message: string }
export interface Report { errors: Finding[]; warnings: Finding[]; count: number; files: number }

const ID_RE = /^oc_[0-9a-f]{12}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const SIZE_RE = /^[0-9.]+ ?(ml|g|kg|l|pcs)$/;
const AFFILIATE_RE = /(affid=|[?&]tag=[a-z0-9-]+-\d\d|utm_)/i;
const LIVE_FIELDS = ["price", "mrp", "selling_price", "stock", "in_stock", "availability", "discount", "offers"];
/** The latest day it plausibly is, anywhere the contributor might be.
 *
 *  `toISOString` is UTC and this dataset is written from IST. Between midnight
 *  and 05:30 local, a date a crawler stamps as today is still tomorrow in UTC,
 *  and every record written in that window was rejected as being from the
 *  future — 387 of them in one run. A date counts as future only when it is
 *  ahead of both readings. */
export function today(): string {
  const now = new Date();
  const utcDay = now.toISOString().slice(0, 10);
  const localDay =
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  return localDay > utcDay ? localDay : utcDay;
}

const SOURCE_KINDS = new Set(["brand-store", "brand-submitted", "marketplace-feed", "marketplace-api", "extension", "manual", "ocr"]);

/** Check one attribute against its declared spec. Returns messages, never throws. */
export function checkAttribute(key: string, spec: FieldSpec, value: AttrValue): string[] {
  const out: string[] = [];
  if (value === null || value === "") return out;

  switch (spec.type) {
    case "integer":
      if (!Number.isInteger(value)) out.push(`${key} must be an integer, got ${JSON.stringify(value)}`);
      break;
    case "number":
      if (typeof value !== "number" || Number.isNaN(value)) out.push(`${key} must be a number, got ${JSON.stringify(value)}`);
      break;
    case "enum":
      if (!spec.values?.includes(String(value))) out.push(`${key}=${JSON.stringify(value)} is not one of ${spec.values?.join(", ")}`);
      break;
    case "list":
      if (!Array.isArray(value)) { out.push(`${key} must be a list`); break; }
      if (spec.values) for (const v of value) if (!spec.values.includes(v)) out.push(`${key} contains "${v}", which is not in the declared vocabulary`);
      return out;
    case "quantity":
      if (typeof value !== "string" || !SIZE_RE.test(value)) out.push(`${key}=${JSON.stringify(value)} should look like "30 ml"`);
      return out;
    case "boolean":
      if (typeof value !== "boolean") out.push(`${key} must be true or false`);
      return out;
  }
  if (typeof value === "number") {
    if (spec.min !== undefined && value < spec.min) out.push(`${key}=${value} is below the minimum ${spec.min}`);
    if (spec.max !== undefined && value > spec.max) out.push(`${key}=${value} is above the maximum ${spec.max}`);
  }
  return out;
}

interface State {
  ids: Map<string, string>;
  gtins: Map<string, string>;
  keys: Map<string, string>;
  today: string;
  /** Every superseded_by pointer seen, checked once every id is known.
      A record may point at one that appears later in file order, so this
      cannot be resolved while walking. */
  supersedes: Array<{ file: string; line: number; from: string; to: string }>;
}

/** Validate a single record. Exported so tests can call it directly. */
export function validateRecord(
  r: ProductRecord, file: string, line: number,
  schemas: Map<string, DomainSchema>, state: State,
): { errors: Finding[]; warnings: Finding[] } {
  const errors: Finding[] = [], warnings: Finding[] = [];
  const E = (code: string, message: string) => errors.push({ file, line, code, message });
  const W = (code: string, message: string) => warnings.push({ file, line, code, message });

  for (const k of ["id", "name", "brand", "domain", "category", "sources"] as const) {
    const v = r[k];
    if (v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0)) E("E2", `missing required field "${k}"`);
  }
  for (const k of Object.keys(r)) if (!TOP_LEVEL_FIELDS.has(k)) E("E2", `unknown top-level field "${k}"`);

  if (!ID_RE.test(r.id ?? "")) E("E3", `id "${r.id}" must match oc_<12 hex> — run: npm run mint -- "Brand" "Name" "30 ml"`);
  else if (state.ids.has(r.id)) E("E3", `duplicate id ${r.id} (already at ${state.ids.get(r.id)})`);
  else state.ids.set(r.id, `${rel(file)}:${line}`);

  // A superseded record points at the one that replaced it. The repo's first
  // cross-record reference, so it needs the check every reference needs: the
  // target must exist, and nothing may supersede itself.
  const sup = r.superseded_by;
  if (sup !== undefined && sup !== null && sup !== "") {
    if (!ID_RE.test(sup)) E("E12", `superseded_by "${sup}" must match oc_<12 hex>`);
    else if (sup === r.id) E("E12", `record supersedes itself`);
    else state.supersedes.push({ file, line, from: r.id ?? "", to: sup });
  }

  const want = brandFileFor(r.domain, r.brand ?? "");
  if (want !== rel(file)) E("E4", `this record belongs in ${want}, not ${rel(file)}`);

  const ds = schemas.get(r.domain);
  if (!ds) { E("E5", `no schema for domain "${r.domain}" — add schemas/${r.domain}.json`); return { errors, warnings }; }

  const cs = ds.categories[r.category] ?? ds.categories["_default"];
  if (!cs) { E("E5", `category "${r.category}" is not declared in schemas/${r.domain}.json`); return { errors, warnings }; }

  const attrs = r.attributes ?? {};
  for (const [k, v] of Object.entries(attrs)) {
    const spec = ds.fields[k];
    if (!spec) { E("E7", `attribute "${k}" is not declared in schemas/${r.domain}.json`); continue; }
    for (const m of checkAttribute(k, spec, v)) E("E7", m);
  }

  const missing = (cs.required ?? []).filter((k) => {
    const v = attrs[k];
    return v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
  });
  // The status vocabulary is declared in schema.ts but was never enforced, so
  // a typo ("retired" for "discontinued") validated cleanly and 17 records
  // carried a value nothing downstream understands.
  const STATUSES = new Set(["entry", "candidate", "disputed", "discontinued"]);
  if (r.status !== undefined && r.status !== null && !STATUSES.has(r.status))
    E("E2", `status "${r.status}" is not one of ${[...STATUSES].join(", ")}`);

  const status = r.status ?? "entry";
  if (missing.length && status === "entry")
    E("E6", `category "${r.category}" requires [${cs.required}]; missing [${missing}]. Supply them, or set "status":"candidate".`);

  for (const s of r.sources ?? []) {
    if (!SOURCE_KINDS.has(s.kind)) E("E8", `source kind "${s.kind}" is not allowed`);
    if (!DATE_RE.test(s.checked ?? "")) E("E8", `source.checked "${s.checked}" must be YYYY-MM-DD`);
    else if (s.checked > state.today) E("E8", `source.checked ${s.checked} is in the future`);
  }

  const ids = r.identifiers ?? {};
  if (ids.gtin) {
    if (!gtinValid(ids.gtin)) E("E9", `GTIN ${ids.gtin} fails the check digit`);
    // a retired record carries its replacement's barcode by design
    else if (r.superseded_by) { /* not a clash */ }
    else if (state.gtins.has(ids.gtin)) W("W1", `GTIN ${ids.gtin} is also on ${state.gtins.get(ids.gtin)}`);
    else state.gtins.set(ids.gtin, r.id);
  }
  for (const k of Object.keys(ids)) if (!(IDENTIFIER_KEYS as readonly string[]).includes(k))
    E("E9", `identifier "${k}" is not declared — add it to schemas/product.json first`);
  if (ids.isin && !/^INF[A-Z0-9]{9}$/.test(ids.isin)) E("E9", `isin "${ids.isin}" is malformed`);
  if (ids.asin && !/^[A-Z0-9]{10}$/.test(ids.asin)) E("E9", `asin "${ids.asin}" is malformed`);
  if (ids.fsn && !/^[A-Z0-9]{16}$/.test(ids.fsn)) E("E9", `fsn "${ids.fsn}" is malformed`);

  // E11 — the identity floor. A candidate is a record we published with a fact
  // missing; it is still a record someone can recognise and finish. A record
  // nobody can identify is not a gap, it is noise, and no contributor can ever
  // fix it because they cannot tell what the product is.
  const letters = [...(r.name ?? "")].filter((c) => /\p{L}/u.test(c)).length;
  if (letters < 3)
    E("E11", `name "${r.name}" does not identify a product — fewer than 3 letters. ` +
             `A barcode or an emoji as a name is noise, not an incomplete record.`);
  if (/^[\d\s\-]+$/.test(r.name ?? ""))
    E("E11", `name "${r.name}" is a barcode, not a product name`);
  if ((r.brand ?? "").trim().length < 2 || /^\d+$/.test((r.brand ?? "").trim()))
    E("E11", `brand "${r.brand}" is not a brand`);

  const blob = JSON.stringify(r);
  for (const k of LIVE_FIELDS) if (blob.includes(`"${k}"`)) E("E10", `"${k}" is live data — it belongs in the service, not this repo`);
  if (AFFILIATE_RE.test(blob)) E("E10", "an affiliate tag or tracking parameter is in a URL; store clean canonical URLs");

  // The pack is part of what a product is: most records carry it in
  // `attributes.quantity`, not `size`, and keying on `size` alone called 871
  // pairs like "100 ml" and "2 x 100 ml" duplicates (measured 2026-09-30).
  // A record that names its replacement is a duplicate by design, not a find.
  const pack = r.size ?? r.attributes?.quantity ?? "";
  const key = `${norm(r.brand)}|${norm(r.name)}|${norm(String(pack))}`;
  if (!r.superseded_by) {
    if (state.keys.has(key)) W("W2", `looks like a duplicate of ${state.keys.get(key)}`);
    else state.keys.set(key, r.id);
  }

  if (r.domain === "appliances" && Number(attrs.star ?? 0) >= 4 && !attrs.rating_year)
    W("W3", "BEE star rating of 4 or more with no rating_year — thresholds are revised, so this can mislead");

  // A nutrition panel that contradicts itself. These are faithful reads: the
  // source page really does declare "Total Fat 0 g" beside "Saturated Fat 16 g",
  // so the figure is not ours to correct — but a component cannot exceed the
  // total it belongs to, and publishing both without a mark would pass the
  // contradiction on silently. Tolerances absorb honest rounding on a panel
  // that declares to one decimal.
  if (r.domain === "grocery") {
    const n = (k: string) => (typeof attrs[k] === "number" ? (attrs[k] as number) : null);
    const fat = n("fat_100g"), sat = n("saturated_fat_100g");
    const carb = n("carbohydrates_100g"), sug = n("sugars_100g"), add = n("added_sugar_100g");
    const pro = n("proteins_100g");
    if (fat !== null && sat !== null && sat > fat + 0.5)
      W("W5", `saturated fat ${sat} g exceeds total fat ${fat} g per 100 g — the source panel contradicts itself`);
    if (carb !== null && sug !== null && sug > carb + 1)
      W("W5", `sugars ${sug} g exceed carbohydrates ${carb} g per 100 g — the source panel contradicts itself`);
    if (sug !== null && add !== null && add > sug + 1)
      W("W5", `added sugar ${add} g exceeds total sugars ${sug} g per 100 g — the source panel contradicts itself`);
    if (fat !== null && carb !== null && pro !== null && fat + carb + pro > 101)
      W("W5", `fat, carbohydrate and protein sum to ${(fat + carb + pro).toFixed(1)} g per 100 g — the source panel contradicts itself`);
  }

  return { errors, warnings };
}

export function validateAll(): Report {
  const schemas = loadDomainSchemas();
  const state: State = {
    ids: new Map(), gtins: new Map(), keys: new Map(), today: today(), supersedes: [],
  };
  const errors: Finding[] = [], warnings: Finding[] = [];
  const files = productFiles();
  let count = 0;

  for (const file of files) {
    let prev: { c: string; n: string; i: string } | null = null;
    for (const item of readRecords(file)) {
      if ("error" in item) { errors.push({ file, line: item.line, code: "E1", message: item.error }); continue; }
      count++;
      const res = validateRecord(item.record, file, item.line, schemas, state);
      errors.push(...res.errors); warnings.push(...res.warnings);
      const r = item.record;
      const key = { c: r.category ?? "", n: (r.name ?? "").toLowerCase(), i: r.id ?? "" };
      if (prev !== null) {
        const cmp = key.c.localeCompare(prev.c) || key.n.localeCompare(prev.n) || key.i.localeCompare(prev.i);
        if (cmp < 0) warnings.push({ file, line: item.line, code: "W4", message: "lines are out of canonical order — run: npm run format" });
      }
      prev = key;
    }
  }
  // Now that every id is known, resolve the superseded_by pointers.
  for (const { file, line, from, to } of state.supersedes) {
    if (!state.ids.has(to)) {
      errors.push({ file, line, code: "E12",
        message: `superseded_by ${to} names no record — the replacement must exist (from ${from})` });
    }
  }

  return { errors, warnings, count, files: files.length };
}

if (import.meta.filename === process.argv[1]) {
  const { errors, warnings, count, files } = validateAll();
  console.log(`checked ${count} records in ${files} files`);
  for (const w of warnings.slice(0, 60)) console.log(`  warn  ${rel(w.file)}:${w.line}  [${w.code}] ${w.message}`);
  if (warnings.length > 60) console.log(`  … and ${warnings.length - 60} more warnings`);
  for (const e of errors.slice(0, 120)) console.log(`  ERROR ${rel(e.file)}:${e.line}  [${e.code}] ${e.message}`);
  if (errors.length > 120) console.log(`  … and ${errors.length - 120} more errors`);
  console.log(`\n${errors.length} errors, ${warnings.length} warnings`);
  process.exit(errors.length ? 1 : 0);
}
