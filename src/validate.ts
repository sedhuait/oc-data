import {
  ROOT, TOP_LEVEL_FIELDS, brandFileFor, gtinValid, loadDomainSchemas, norm,
  productFiles, readRecords, rel,
  type AttrValue, type DomainSchema, type FieldSpec, type ProductRecord,
} from "./schema.ts";

export interface Finding { file: string; line: number; code: string; message: string }
export interface Report { errors: Finding[]; warnings: Finding[]; count: number; files: number }

const ID_RE = /^oc_[0-9a-f]{12}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const SIZE_RE = /^[0-9.]+ ?(ml|g|kg|l|pcs)$/;
const AFFILIATE_RE = /(affid=|[?&]tag=[a-z0-9-]+-\d\d|utm_)/i;
const LIVE_FIELDS = ["price", "mrp", "selling_price", "stock", "in_stock", "availability", "discount", "offers"];
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
    else if (state.gtins.has(ids.gtin)) W("W1", `GTIN ${ids.gtin} is also on ${state.gtins.get(ids.gtin)}`);
    else state.gtins.set(ids.gtin, r.id);
  }
  if (ids.asin && !/^[A-Z0-9]{10}$/.test(ids.asin)) E("E9", `asin "${ids.asin}" is malformed`);
  if (ids.fsn && !/^[A-Z0-9]{16}$/.test(ids.fsn)) E("E9", `fsn "${ids.fsn}" is malformed`);

  const blob = JSON.stringify(r);
  for (const k of LIVE_FIELDS) if (blob.includes(`"${k}"`)) E("E10", `"${k}" is live data — it belongs in the service, not this repo`);
  if (AFFILIATE_RE.test(blob)) E("E10", "an affiliate tag or tracking parameter is in a URL; store clean canonical URLs");

  const key = `${norm(r.brand)}|${norm(r.name)}|${r.size ?? ""}`;
  if (state.keys.has(key)) W("W2", `looks like a duplicate of ${state.keys.get(key)}`);
  else state.keys.set(key, r.id);

  if (r.domain === "appliances" && Number(attrs.star ?? 0) >= 4 && !attrs.rating_year)
    W("W3", "BEE star rating of 4 or more with no rating_year — thresholds are revised, so this can mislead");

  return { errors, warnings };
}

export function validateAll(): Report {
  const schemas = loadDomainSchemas();
  const state: State = { ids: new Map(), gtins: new Map(), keys: new Map(), today: new Date().toISOString().slice(0, 10) };
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
