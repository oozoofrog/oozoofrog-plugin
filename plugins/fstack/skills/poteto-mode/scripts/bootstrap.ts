import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { homedir } from "node:os";
import { join } from "node:path";

// Production packages may be read-only. Install the locked parser once per lockfile.
export function loadCommander(): typeof import("commander") {
  const source = import.meta.dir;
  const hash = createHash("sha256");
  for (const name of ["package.json", "bun.lock"]) hash.update(readFileSync(join(source, name)));
  const root = process.env.FSTACK_CACHE_DIR ||
    join(process.env.XDG_CACHE_HOME || join(homedir(), ".cache"), "fstack");
  const target = join(root, hash.digest("hex"));
  const parser = join(target, "node_modules", "commander", "package.json");
  if (!existsSync(parser)) {
    mkdirSync(root, { recursive: true });
    const stage = mkdtempSync(join(root, ".watch-pr-"));
    try {
      for (const name of ["package.json", "bun.lock"]) copyFileSync(join(source, name), join(stage, name));
      const install = Bun.spawnSync([process.execPath, "install", "--production", "--frozen-lockfile"], {
        cwd: stage, stdout: "pipe", stderr: "pipe",
        env: { ...process.env, BUN_INSTALL_CACHE_DIR: process.env.BUN_INSTALL_CACHE_DIR || join(root, "bun") },
      });
      if (install.exitCode !== 0) throw new Error("Cannot provision watch-pr: " + install.stderr.toString());
      try {
        renameSync(stage, target);
      } catch (error) {
        if (!existsSync(parser)) throw error;
      }
    } finally {
      rmSync(stage, { recursive: true, force: true });
    }
  }
  return createRequire(join(target, "package.json"))("commander");
}
