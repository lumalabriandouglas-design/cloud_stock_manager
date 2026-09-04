#!/usr/bin/env node
import { existsSync, readdirSync } from "node:fs";
import { spawn } from "node:child_process";

const port = String(process.env.PORT || "8080");
const env = {
  ...process.env,
  PORT: port,
  NITRO_PORT: port,
  HOST: "0.0.0.0",
  NITRO_HOST: "0.0.0.0",
  LISTEN_ADDRESS: "0.0.0.0",
};

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: "inherit", env });
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(" ")} exited ${code}`));
    });
  });
}

const candidates = [
  ".output/server/index.mjs",
  ".output/server/index.js",
  "server/index.mjs",
];
const serverFile = candidates.find((file) => existsSync(file));
console.log(`[start] port=${port} server=${serverFile || "missing"}`);
if (!serverFile) {
  console.log("[start] files:", readdirSync(".").join(", "));
}

// Do not block the port on migrate. Schema also applies on first request.
run("node", ["scripts/migrate.mjs"]).catch((err) => console.error(err.message));

if (serverFile) {
  await run("node", [serverFile]);
} else {
  await run("npx", ["vite", "preview", "--host", "0.0.0.0", "--port", port]);
}
