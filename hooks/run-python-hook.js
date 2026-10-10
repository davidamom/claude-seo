#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");

const PROBE_SCRIPT = "import sys; print(sys.executable); print(sys.version.split()[0])";
const VERSION_LINE = /^\d+\.\d+/;
// The Microsoft Store placeholder (AppInstallerPythonRedirector.exe) prints a hint
// instead of running Python. The hint is the signal; the interpreter path is not,
// because Store Python itself lives under WindowsApps.
const STORE_STUB_MESSAGE = /Microsoft Store|App execution alias|was not found|n.o foi encontrado/i;

function stripWrappingQuotes(value) {
  return value.replace(/^["']|["']$/g, "");
}

function pythonCandidates() {
  const candidates = [];
  if (process.env.CLAUDE_SEO_PYTHON) {
    candidates.push({
      label: "CLAUDE_SEO_PYTHON",
      exe: stripWrappingQuotes(process.env.CLAUDE_SEO_PYTHON),
      args: [],
    });
  }
  candidates.push(
    { label: "py -3", exe: "py", args: ["-3"] },
    { label: "python3", exe: "python3", args: [] },
    { label: "python", exe: "python", args: [] },
  );
  return candidates;
}

function isStoreStubOutput(text) {
  return STORE_STUB_MESSAGE.test(String(text || ""));
}

function probeAccepts(status, stdout, stderr) {
  if (status !== 0) {
    return false;
  }
  const lines = String(stdout || "").trim().split(/\r?\n/);
  if (lines.length < 2 || !VERSION_LINE.test(lines[lines.length - 1])) {
    return false;
  }
  return !isStoreStubOutput(stderr);
}

function probe(candidate) {
  const result = spawnSync(candidate.exe, [...candidate.args, "-c", PROBE_SCRIPT], {
    encoding: "utf8",
  });
  return probeAccepts(result.status, result.stdout, result.stderr);
}

function main() {
  const [, , hookScript, ...hookArgs] = process.argv;
  if (!hookScript) {
    process.exit(0);
  }

  for (const candidate of pythonCandidates()) {
    if (!probe(candidate)) {
      continue;
    }
    const result = spawnSync(candidate.exe, [...candidate.args, hookScript, ...hookArgs], {
      stdio: "inherit",
    });
    if (result.error) {
      continue;
    }
    process.exit(result.status === null ? 1 : result.status);
  }

  console.error(
    "Claude SEO hook could not find Python. Tried CLAUDE_SEO_PYTHON, py -3, python3, python.",
  );
  process.exit(1);
}

module.exports = { isStoreStubOutput, probeAccepts };

if (require.main === module) {
  main();
}
