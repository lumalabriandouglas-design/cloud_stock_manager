#!/usr/bin/env node
import { existsSync, readdirSync } from "node:fs";
import { spawn } from "node:child_process";

const port = String(process.env.PORT || "8080");
const publicDomain = (process.env.RAILWAY_PUBLIC_DOMAIN || "").trim();
const betterAuthUrl =
  (process.env.BETTER_AUTH_URL || "").trim() ||
  (publicDomain ? `https://${publicDomain}` : "");

const env = {
  ...process.env,
  PORT: port,
  NITRO_PORT: port,
  HOST: "0.0.0.0",
  NITRO_HOST: "0.0.0.0",
  LISTEN_ADDRESS: "0.0.0.0",
};

if (betterAuthUrl && !process.env.BETTER_AUTH_URL) {
  env.BETTER_AUTH_URL = betterAuthUrl;
}
if (!process.env.BETTER_AUTH_SECRET) {
  env.BETTER_AUTH_SECRET =
    process.env.RAILWAY_PROJECT_ID ||
    "cloud-stock-manager-change-me-in-railway";
}

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
console.log(
  `[start] port=${port} host=0.0.0.0 server=${serverFile || "missing"} authUrl=${env.BETTER_AUTH_URL || "unset"}`,
);
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
