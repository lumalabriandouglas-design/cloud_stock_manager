import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const srcDir = join(root, "node_modules/@electric-sql/pglite/dist");
const dests = [
  join(root, ".output/server/_libs"),
  join(root, ".output/server"),
];
const files = ["pglite.data", "pglite.wasm", "initdb.wasm"];

for (const dest of dests) {
  if (!existsSync(dirname(dest))) continue;
  mkdirSync(dest, { recursive: true });
  for (const file of files) {
    const from = join(srcDir, file);
    if (!existsSync(from)) continue;
    copyFileSync(from, join(dest, file));
    console.log("[pglite] copied", file, "->", dest);
  }
}
