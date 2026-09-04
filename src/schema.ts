import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname, relative, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

/* ---------- the record shape: one source of truth for every tool ---------- */

export type SourceKind =
  | "brand-store" | "brand-submitted" | "marketplace-feed"
  | "marketplace-api" | "extension" | "manual" | "ocr";

export interface Source {
  kind: SourceKind;
  url?: string | null;
  checked: string;            // YYYY-MM-DD
  note?: string | null;
}

export interface Identifiers {
  gtin?: string | null;
  asin?: string | null;
  fsn?: string | null;
  ondc?: string | null;
  shopify_handle?: string | null;
}

export interface Variant {
  name: string;
  sku?: string | null;
  gtin?: string | null;
  overrides?: Record<string, AttrValue>;
}

export type AttrValue = string | number | boolean | string[] | null;

export interface ProductRecord {
  id: string;                 // oc_<12 hex> — never reused, never changed
  slug?: string;
  name: string;
  brand: string;
  line?: string | null;
  domain: string;
  category: string;
  size?: string | null;
  identifiers?: Identifiers;
  attributes?: Record<string, AttrValue>;
  ingredients?: string[];
  variants?: Variant[];
  images?: string[];
  urls?: { brand?: string | null; flipkart?: string | null; amazon?: string | null };
  status?: "entry" | "candidate" | "disputed" | "discontinued";
  confidence?: "stated" | "extracted" | "verified";
  sources: Source[];
  first_seen?: string | null;
  superseded_by?: string | null;
}

/* ---------- schemas on disk ---------- */

export interface FieldSpec {
  type: "string" | "integer" | "number" | "enum" | "list" | "quantity" | "boolean";
  values?: string[];
  units?: string[];
  min?: number;
  max?: number;
  unit?: string;
  label?: string;
  note?: string;
}

export interface CategorySpec {
  required?: string[];
  columns?: string[];
  facets?: string[];
}

export interface DomainSchema {
  domain: string;
  label: string;
  categories: Record<string, CategorySpec>;
  fields: Record<string, FieldSpec>;
  sanity?: Record<string, unknown>;
}

export function loadDomainSchemas(): Map<string, DomainSchema> {
  const dir = join(ROOT, "schemas");
  const out = new Map<string, DomainSchema>();
  for (const f of readdirSync(dir)) {
    if (!f.endsWith(".json") || f === "product.json") continue;
    const s = JSON.parse(readFileSync(join(dir, f), "utf8")) as DomainSchema;
    out.set(s.domain, s);
  }
  return out;
}

export const TOP_LEVEL_FIELDS = new Set<keyof ProductRecord | string>([
  "id", "slug", "name", "brand", "line", "domain", "category", "size", "identifiers",
  "attributes", "ingredients", "variants", "images", "urls", "status", "confidence",
  "sources", "first_seen", "superseded_by",
]);

/* ---------- files ---------- */

export interface Loaded { file: string; line: number; record: ProductRecord; raw: string }

export function productFiles(): string[] {
  const base = join(ROOT, "products");
  const out: string[] = [];
  const walk = (d: string) => {
    for (const e of readdirSync(d)) {
      const p = join(d, e);
      if (statSync(p).isDirectory()) walk(p);
      else if (e.endsWith(".jsonl")) out.push(p);
    }
  };
  try { walk(base); } catch { /* no products yet */ }
  return out.sort();
}

export function* readRecords(file: string): Generator<Loaded | { file: string; line: number; error: string; raw: string }> {
  const text = readFileSync(file, "utf8");
  let line = 0;
  for (const raw of text.split("\n")) {
    line++;
    if (!raw.trim()) continue;
    try {
      const record = JSON.parse(raw) as ProductRecord;
      if (typeof record !== "object" || record === null || Array.isArray(record)) {
        yield { file, line, error: "each line must be one JSON object", raw };
        continue;
      }
      yield { file, line, record, raw };
    } catch (e) {
      yield { file, line, error: `not valid JSON: ${(e as Error).message}`, raw };
    }
  }
}

/* ---------- shared helpers ---------- */

export const norm = (s: string): string =>
  (s ?? "").normalize("NFKD").toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();

export const slugify = (s: string): string =>
  norm(s).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export const mintId = (brand: string, name: string, size = ""): string =>
  "oc_" + createHash("sha1").update(`${norm(brand)}|${norm(name)}|${size.replace(/\s/g, "")}`).digest("hex").slice(0, 12);

export const rel = (f: string): string => relative(ROOT, f);
export const brandFileFor = (domain: string, brand: string): string =>
  join("products", domain, slugify(brand) + ".jsonl");

export function gtinValid(g: string): boolean {
  if (!/^\d+$/.test(g) || ![8, 12, 13, 14].includes(g.length)) return false;
  const digits = [...g].map(Number).reverse();
  const sum = digits.reduce((acc, d, i) => acc + d * (i % 2 ? 3 : 1), 0);
  return sum % 10 === 0;
}

export const canonical = (r: ProductRecord): string =>
  JSON.stringify(r, Object.keys(r).sort());

export { basename };
