import { mintId, slugify } from "./schema.ts";

const [brand, name, size = ""] = process.argv.slice(2);
if (!brand || !name) {
  console.error('Usage: npm run mint -- "Brand" "Product name" ["30 ml"]');
  process.exit(1);
}
console.log(mintId(brand, name, size));
console.log("slug:", slugify(`${brand} ${name}`).slice(0, 80));
