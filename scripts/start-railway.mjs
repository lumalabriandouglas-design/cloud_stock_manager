#!/usr/bin/env node
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";

const port = process.env.PORT || "8080";

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: "inherit",
      env: { ...process.env, PORT: port, NITRO_PORT: port, HOST: "0.0.0.0" },
    });
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(" ")} exited ${code}`));
    });
  });
}

await run("node", ["scripts/migrate.mjs"]).catch((err) => {
  console.error(err.message);
});

if (existsSync(".output/server/index.mjs")) {
  await run("node", [".output/server/index.mjs"]);
} else {
  await run("node", [
    "scripts/with-app-env.mjs",
    "vite",
    "preview",
    "--host",
    "0.0.0.0",
    "--port",
    port,
  ]);
}
