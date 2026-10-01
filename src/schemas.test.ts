import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { loadDomainSchemas, ROOT } from "./schema.ts";
import type { DomainSchema } from "./schema.ts";

const schemas = loadDomainSchemas();
const domains = [...schemas.values()];

/**
 * Keys whose label alone answers "what is it, how do I read it, how do I use
 * it". `Weight — 187 g` needs no gloss; `Deposit insurance — DICGC up to
 * ₹5 lakh` needs all three. Identifiers and document pointers are exempt
 * because the label is self-describing and the value is a URL or a code.
 *
 * This list is deliberately explicit so the note requirement is deterministic
 * and every addition shows up as a reviewable diff.
 */
const SELF_EVIDENT = new Set([
  "size", "quantity", "serving_size", "weight_g", "year", "launch_month",
  "shade", "colour", "color", "form", "texture", "brand", "name",
  "screen_in", "resolution_px", "nodes", "antennas", "usb_ports", "lan_ports",
  "sim_slots", "min_age", "max_age", "min_entry_age", "max_entry_age",
  "country_of_origin", "manufacturer", "shelf_life", "launch_date",
  "os", "gpu", "soc", "mitc_url", "mitc_version", "charges_url",
  "charges_version", "policy_wording_url", "brochure_url", "wording_version",
  "scheme_code", "isin_growth", "isin_reinvest", "fssai_licence",
  "cartridge_model", "fits_models", "paper_sizes", "type", "finish",
]);

/** Facet keys that aren't attributes — they read off the record itself. */
const SYNTHETIC_FACETS = new Set(["brand", "size", "category"]);

/** The validator's own live-data tokens (validate.ts LIVE_FIELDS). A schema
 *  key with one of these names becomes a record key the moment anyone fills
 *  it in, and E10 would then reject the record. Catch it here instead. */
const LIVE_FIELDS = [
  "price", "selling_price", "stock", "in_stock", "availability",
  "discount", "offers",
];

/** Editorial judgments. The catalogue records facts and never ranks. */
const EDITORIAL = [
  "rating", "score", "best_for", "recommendation", "rank", "review_count",
  "approval_odds", "healthiness", "riskometer",
];

/**
 * Advice phrasing that turns a factual note into a buying recommendation.
 * Deliberately targets second-person and superlative steers ("you should
 * buy", "the best option") rather than the bare word "recommended", which
 * legitimately appears in makers' own spec names — a printer's
 * "recommended monthly volume" is a published figure, not our opinion.
 */
const ADVICE_RE =
  /\b(you should|we recommend|our pick|the best\b|the worst\b|worth buying|avoid buying|go for the|opt for the)\b/i;

describe("schema referential integrity", () => {
  test("every columns/facets/spec/required key is a declared field", () => {
    for (const ds of domains) {
      for (const [cat, cs] of Object.entries(ds.categories)) {
        for (const key of cs.required ?? [])
          assert.ok(ds.fields[key], `${ds.domain}/${cat} required "${key}" is not in fields`);
        for (const key of cs.columns ?? [])
          assert.ok(ds.fields[key], `${ds.domain}/${cat} columns "${key}" is not in fields`);
        for (const key of cs.spec ?? [])
          assert.ok(ds.fields[key], `${ds.domain}/${cat} spec "${key}" is not in fields`);
        for (const key of cs.facets ?? []) {
          if (SYNTHETIC_FACETS.has(key)) continue;
          assert.ok(ds.fields[key], `${ds.domain}/${cat} facets "${key}" is not in fields`);
        }
      }
    }
  });

  test("columns is a subset of spec wherever spec is declared", () => {
    for (const ds of domains) {
      for (const [cat, cs] of Object.entries(ds.categories)) {
        if (!cs.spec?.length) continue;
        const spec = new Set(cs.spec);
        for (const key of cs.columns ?? [])
          assert.ok(spec.has(key),
            `${ds.domain}/${cat}: "${key}" is in columns but missing from spec`);
      }
    }
  });

  test("spec arrays have no duplicate keys", () => {
    for (const ds of domains) {
      for (const [cat, cs] of Object.entries(ds.categories)) {
        const spec = cs.spec ?? [];
        assert.equal(new Set(spec).size, spec.length, `${ds.domain}/${cat} spec has duplicates`);
      }
    }
  });

  test("every field group is declared in the domain's groups", () => {
    for (const ds of domains) {
      const ids = new Set((ds.groups ?? []).map((g) => g.id));
      for (const [key, spec] of Object.entries(ds.fields)) {
        if (!spec.group) continue;
        assert.ok(ids.has(spec.group),
          `${ds.domain}.${key} has group "${spec.group}" which is not in groups`);
      }
    }
  });

  test("group ids are unique and every declared group is used", () => {
    for (const ds of domains) {
      const groups = ds.groups ?? [];
      const ids = groups.map((g) => g.id);
      assert.equal(new Set(ids).size, ids.length, `${ds.domain} has duplicate group ids`);
      const used = new Set(Object.values(ds.fields).map((f) => f.group).filter(Boolean));
      for (const id of ids)
        assert.ok(used.has(id), `${ds.domain} declares group "${id}" but no field uses it`);
    }
  });

  test("values_note only glosses values the enum actually has", () => {
    for (const ds of domains) {
      for (const [key, spec] of Object.entries(ds.fields)) {
        if (!spec.values_note) continue;
        const values = new Set(spec.values ?? []);
        for (const v of Object.keys(spec.values_note))
          assert.ok(values.has(v),
            `${ds.domain}.${key} values_note glosses "${v}", which is not a declared value`);
      }
    }
  });
});

describe("the required-fields freeze", () => {
  // Adding a key to `required` fails E6 on every existing status:"entry"
  // record that lacks it. With 24,527 records live, that is not a change to
  // make by accident — so it has to be made here, on purpose, in a diff.
  test("required matches the checked-in snapshot", () => {
    const snapshot = JSON.parse(
      readFileSync(join(ROOT, "src/required.snapshot.json"), "utf8")
    ) as Record<string, Record<string, string[]>>;

    const actual: Record<string, Record<string, string[]>> = {};
    for (const ds of domains) {
      actual[ds.domain] = {};
      for (const cat of Object.keys(ds.categories).sort())
        actual[ds.domain]![cat] = ds.categories[cat]!.required ?? [];
    }

    assert.deepEqual(actual, snapshot,
      "`required` changed. That invalidates existing entry records (E6). " +
      "If this is deliberate, demote the affected records to candidate and " +
      "update src/required.snapshot.json in the same commit.");
  });
});

describe("banned field names", () => {
  test("no field is named after live data", () => {
    for (const ds of domains)
      for (const key of Object.keys(ds.fields))
        assert.ok(!LIVE_FIELDS.includes(key),
          `${ds.domain}.${key} is live data — it belongs in the service (E10)`);
  });

  test("no field is an editorial judgment", () => {
    for (const ds of domains)
      for (const key of Object.keys(ds.fields))
        assert.ok(!EDITORIAL.includes(key),
          `${ds.domain}.${key} is a judgment, not a fact`);
  });

  test("nothing in a domain's own not_in_this_repo leaks into a spec sheet", () => {
    for (const ds of domains) {
      const banned = new Set(ds.not_in_this_repo ?? []);
      if (!banned.size) continue;
      for (const [cat, cs] of Object.entries(ds.categories))
        for (const key of cs.spec ?? [])
          assert.ok(!banned.has(key),
            `${ds.domain}/${cat} spec includes "${key}", which ${ds.domain} declares not_in_this_repo`);
    }
  });

  test("field names are lower snake_case", () => {
    for (const ds of domains)
      for (const key of Object.keys(ds.fields))
        assert.match(key, /^[a-z][a-z0-9_]*$/, `${ds.domain}.${key} is not snake_case`);
  });
});

describe("schema changes stay backward compatible", () => {
  // A field's declared type, its enum values and its numeric bounds are a
  // contract with 24,527 records that already exist. Widening a bound is
  // safe; narrowing one, dropping an enum value, or retyping a field
  // retroactively invalidates records that were valid when written — which
  // is exactly how `colour: "Colour"` briefly became 196 E7 errors.
  const HEAD = (file: string): DomainSchema | null => {
    try {
      const raw = execFileSync("git", ["show", `HEAD:schemas/${file}`], {
        cwd: ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"],
      });
      return JSON.parse(raw) as DomainSchema;
    } catch {
      return null; // new schema file, nothing to compare against
    }
  };

  test("no field is retyped, no enum value is dropped, no range is narrowed", () => {
    const broken: string[] = [];
    for (const ds of domains) {
      const before = HEAD(`${ds.domain}.json`);
      if (!before) continue;
      for (const [key, o] of Object.entries(before.fields ?? {})) {
        const c = ds.fields[key];
        if (!c) { broken.push(`${ds.domain}.${key} was removed`); continue; }
        if (o.type !== c.type)
          broken.push(`${ds.domain}.${key} retyped ${o.type} -> ${c.type}`);
        const dropped = (o.values ?? []).filter((v) => !(c.values ?? []).includes(v));
        if (o.values && c.values && dropped.length)
          broken.push(`${ds.domain}.${key} dropped enum values ${dropped.join(", ")}`);
        if (o.min !== undefined && c.min !== undefined && c.min > o.min)
          broken.push(`${ds.domain}.${key} narrowed min ${o.min} -> ${c.min}`);
        if (o.max !== undefined && c.max !== undefined && c.max < o.max)
          broken.push(`${ds.domain}.${key} narrowed max ${o.max} -> ${c.max}`);
      }
    }
    assert.deepEqual(broken, [],
      `these changes would invalidate existing records:\n  ${broken.join("\n  ")}`);
  });
});

describe("every key explains itself", () => {
  test("every field has a label", () => {
    for (const ds of domains)
      for (const [key, spec] of Object.entries(ds.fields))
        assert.ok(spec.label && spec.label.trim().length > 0,
          `${ds.domain}.${key} has no label`);
  });

  test("every field has a note unless it is self-evident", () => {
    const missing: string[] = [];
    for (const ds of domains)
      for (const [key, spec] of Object.entries(ds.fields)) {
        if (SELF_EVIDENT.has(key)) continue;
        if (!spec.note || !spec.note.trim()) missing.push(`${ds.domain}.${key}`);
      }
    assert.deepEqual(missing, [],
      `these fields need a note (what it is, how to read it, how to use it), ` +
      `or an entry in SELF_EVIDENT: ${missing.join(", ")}`);
  });

  test("notes are a useful length", () => {
    for (const ds of domains)
      for (const [key, spec] of Object.entries(ds.fields)) {
        if (!spec.note) continue;
        const n = spec.note.trim().length;
        assert.ok(n >= 20 && n <= 400,
          `${ds.domain}.${key} note is ${n} chars; aim for one to three sentences (20-400)`);
      }
  });

  test("notes explain, they never recommend", () => {
    for (const ds of domains)
      for (const [key, spec] of Object.entries(ds.fields)) {
        if (!spec.note) continue;
        assert.ok(!ADVICE_RE.test(spec.note),
          `${ds.domain}.${key} note reads as buying advice: "${spec.note}"`);
      }
  });
});
