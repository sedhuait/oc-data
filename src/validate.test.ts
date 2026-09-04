import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { validateRecord, checkAttribute } from "./validate.ts";
import { render, clean } from "./format.ts";
import { gtinValid, mintId, slugify, loadDomainSchemas, type ProductRecord } from "./schema.ts";

const schemas = loadDomainSchemas();
const fresh = () => ({ ids: new Map(), gtins: new Map(), keys: new Map(), today: new Date().toISOString().slice(0, 10) });

const good = (over: Partial<ProductRecord> = {}): ProductRecord => ({
  id: "oc_000000000001",
  name: "Niacinamide 10% Face Serum",
  brand: "Minimalist",
  domain: "beauty",
  category: "Face serum",
  size: "30 ml",
  attributes: { size: "30 ml", actives: ["Niacinamide", "Zinc"] },
  sources: [{ kind: "brand-store", url: "https://beminimalist.co/x", checked: "2026-09-04" }],
  ...over,
});

const check = (r: ProductRecord, file = "products/beauty/minimalist.jsonl") =>
  validateRecord(r, file, 1, schemas, fresh());
const codes = (r: ProductRecord, file?: string) => check(r, file).errors.map((e) => e.code);

describe("a well-formed record", () => {
  test("passes with no errors", () => {
    assert.deepEqual(codes(good()), []);
  });
});

describe("the rules that protect the split between facts and live data", () => {
  test("E10 rejects a price", () => {
    assert.ok(codes(good({ price: 499 } as never)).includes("E10"));
  });
  test("E10 rejects stock", () => {
    assert.ok(codes(good({ in_stock: true } as never)).includes("E10"));
  });
  test("E10 rejects an affiliate tag in a URL", () => {
    const r = good({ urls: { brand: "https://www.flipkart.com/x/p/itm1?affid=sedhuaitg" } });
    assert.ok(codes(r).includes("E10"));
  });
  test("a clean canonical URL is fine", () => {
    const r = good({ urls: { brand: "https://www.flipkart.com/x/p/itm1" } });
    assert.deepEqual(codes(r), []);
  });
});

describe("identity", () => {
  test("E3 rejects a malformed id", () => {
    assert.ok(codes(good({ id: "minimalist-serum" })).includes("E3"));
  });
  test("E3 catches a duplicate id within one run", () => {
    const state = fresh();
    validateRecord(good(), "products/beauty/minimalist.jsonl", 1, schemas, state);
    const second = validateRecord(good({ name: "Something else" }), "products/beauty/minimalist.jsonl", 2, schemas, state);
    assert.ok(second.errors.some((e) => e.code === "E3"));
  });
  test("E4 catches a record filed under the wrong brand", () => {
    assert.ok(codes(good({ brand: "Plum" })).includes("E4"));
  });
  test("E9 rejects a GTIN with a bad check digit", () => {
    assert.ok(codes(good({ identifiers: { gtin: "1234567890123" } })).includes("E9"));
  });
  test("a real GTIN passes", () => {
    assert.ok(gtinValid("8901030865275"));
    assert.deepEqual(codes(good({ identifiers: { gtin: "8901030865275" } })), []);
  });
  test("E9 rejects an undeclared identifier key", () => {
    assert.ok(codes(good({ identifiers: { upc: "12345" } as never })).includes("E9"));
  });
  test("E9 checks ISIN format", () => {
    assert.ok(codes(good({ identifiers: { isin: "NOTANISIN" } })).includes("E9"));
    assert.deepEqual(codes(good({ identifiers: { isin: "INF846K01WO1" } })), []);
  });
  test("mintId is stable and size-sensitive", () => {
    assert.equal(mintId("Minimalist", "Niacinamide 10%", "30 ml"), mintId("minimalist", "  Niacinamide 10%  ", "30ml"));
    assert.notEqual(mintId("Minimalist", "Niacinamide 10%", "30 ml"), mintId("Minimalist", "Niacinamide 10%", "60 ml"));
  });
});

describe("category schemas", () => {
  test("E6 blocks an entry missing a required fact", () => {
    const r = good({ category: "Sunscreen", attributes: { size: "50 ml" } });
    assert.ok(codes(r).includes("E6"));
  });
  test("the same record is fine as a candidate", () => {
    const r = good({ category: "Sunscreen", attributes: { size: "50 ml" }, status: "candidate" });
    assert.deepEqual(codes(r), []);
  });
  test("E7 rejects an undeclared attribute", () => {
    assert.ok(codes(good({ attributes: { size: "30 ml", vibe: "nice" } as never })).includes("E7"));
  });
  test("E7 enforces ranges", () => {
    const r = good({ category: "Sunscreen", attributes: { size: "50 ml", spf: 999 } });
    assert.ok(codes(r).includes("E7"));
  });
  test("E7 enforces the declared vocabulary", () => {
    const r = good({ attributes: { size: "30 ml", skin: ["Purple"] } });
    assert.ok(codes(r).includes("E7"));
  });
  test("E5 rejects an unknown category", () => {
    assert.ok(codes(good({ category: "Wizardry", domain: "appliances", brand: "Minimalist" })).includes("E5"));
  });
  test("checkAttribute reports quantity format", () => {
    const msgs = checkAttribute("size", { type: "quantity", units: ["ml"] }, "30ml oops");
    assert.equal(msgs.length, 1);
  });
});

describe("provenance", () => {
  test("E2 rejects a record with no sources", () => {
    assert.ok(codes(good({ sources: [] })).includes("E2"));
  });
  test("E8 rejects a future check date", () => {
    assert.ok(codes(good({ sources: [{ kind: "brand-store", checked: "2099-01-01" }] })).includes("E8"));
  });
  test("E8 rejects an unknown source kind", () => {
    assert.ok(codes(good({ sources: [{ kind: "vibes" as never, checked: "2026-09-04" }] })).includes("E8"));
  });
});

describe("warnings", () => {
  test("W3 flags a star rating with no year", () => {
    const r = good({
      domain: "appliances", brand: "LG", category: "Air conditioners",
      attributes: { capacity_ton: 1.5, star: 5 }, size: null,
    });
    const res = validateRecord(r, "products/appliances/lg.jsonl", 1, schemas, fresh());
    assert.ok(res.warnings.some((w) => w.code === "W3"));
  });
  test("W2 flags a near-duplicate", () => {
    const state = fresh();
    validateRecord(good(), "products/beauty/minimalist.jsonl", 1, schemas, state);
    const dup = validateRecord(good({ id: "oc_000000000002" }), "products/beauty/minimalist.jsonl", 2, schemas, state);
    assert.ok(dup.warnings.some((w) => w.code === "W2"));
  });
});

describe("formatter", () => {
  test("output is deterministic and sorted", () => {
    const a = good({ id: "oc_00000000000b", name: "Zinc serum", category: "Face serum" });
    const b = good({ id: "oc_00000000000a", name: "Alpha serum", category: "Face serum" });
    assert.equal(render([a, b]), render([b, a]));
    const names = render([a, b]).trim().split("\n").map((l) => JSON.parse(l).name);
    assert.deepEqual(names, ["Alpha serum", "Zinc serum"]);
  });
  test("keys are sorted at every level", () => {
    const line = render([good()]).trim();
    const parsed = JSON.parse(line);
    assert.deepEqual(Object.keys(parsed), [...Object.keys(parsed)].sort());
    const src = Object.keys(parsed.sources[0]);
    assert.deepEqual(src, [...src].sort());
  });
  test("nested objects survive formatting", () => {
    const parsed = JSON.parse(render([good()]).trim());
    assert.equal(parsed.sources[0].kind, "brand-store");
    assert.equal(parsed.sources[0].checked, "2026-09-04");
    assert.deepEqual(parsed.attributes.actives, ["Niacinamide", "Zinc"]);
  });
  test("empty values are dropped but containers kept", () => {
    const c = clean(good({ line: null, images: [], attributes: {} }));
    assert.ok(!("line" in c) && !("images" in c) && "attributes" in c);
  });
  test("slugify matches the file naming rule", () => {
    assert.equal(slugify("Dot & Key"), "dot-key");
    assert.equal(slugify("mCaffeine"), "mcaffeine");
  });
});
