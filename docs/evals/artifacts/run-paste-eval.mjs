// Node 24+ 自带 TypeScript 类型擦除。仅加载指定工作树的纯函数，无需项目依赖。
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(process.argv[2] ?? ".");
const corpusPath = fileURLToPath(new URL("./paste-corpus.json", import.meta.url));
const sourcePath = join(root, "apps/web/src/lib/paste.ts");
const hash = (path) => createHash("sha256").update(readFileSync(path)).digest("hex");
const { preparePaste } = await import(pathToFileURL(sourcePath).href);
const corpus = JSON.parse(readFileSync(corpusPath, "utf8"));
const results = corpus.map(({ id, group, input, expected }) => {
  const actual = preparePaste(input);
  const keys = ["text", "format", "title"];
  const mismatch = expected === null || actual === null
    ? (expected === actual ? [] : ["presence"])
    : keys.filter((key) => expected[key] !== actual[key]);
  return { id, group, pass: mismatch.length === 0, mismatch, actual };
});
const git = (...args) => execFileSync("git", ["-C", root, ...args], { encoding: "utf8" }).trim();
const summary = Object.fromEntries(["all", "control", "edge"].map((group) => {
  const selected = results.filter((r) => group === "all" || r.group === group);
  return [group, { pass: selected.filter((r) => r.pass).length, total: selected.length }];
}));
console.log(JSON.stringify({
  revision: git("rev-parse", "HEAD"), sourceChangedFromHead: Boolean(git("status", "--porcelain", "--", "apps/web/src/lib/paste.ts")),
  node: process.version, platform: process.platform, architecture: process.arch,
  corpusSha256: hash(corpusPath), runnerSha256: hash(fileURLToPath(import.meta.url)),
  sourceSha256: hash(sourcePath), summary, results,
}, null, 2));
