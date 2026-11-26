// 从原始返回值重算，不依赖 GenBox 主站源码。用 node verify-records.mjs 运行。
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { isDeepStrictEqual } from "node:util";

function read(name) {
  return readFileSync(new URL(name, import.meta.url), "utf8");
}

const input = read("./paste-corpus.json");
const corpus = JSON.parse(input);
const sha = createHash("sha256").update(input).digest("hex");
const runnerSha = createHash("sha256").update(read("./run-paste-eval.mjs")).digest("hex");
for (const stage of ["backup", "start", "refactor"]) {
  const record = JSON.parse(read("./" + stage + "-paste.json"));
  assert.equal(record.corpusSha256, sha);
  assert.equal(record.runnerSha256, runnerSha);
  assert.equal(record.results.length, corpus.length);
  const scores = { all: { pass: 0, total: 0 }, control: { pass: 0, total: 0 }, edge: { pass: 0, total: 0 } };
  for (const [i, { id, group, expected }] of corpus.entries()) {
    const { id: resultId, group: resultGroup, pass, actual } = record.results[i];
    assert.equal(resultId, id);
    assert.equal(resultGroup, group);
    assert.equal(pass, isDeepStrictEqual(actual, expected), id);
    for (const bucket of [scores.all, scores[group]]) {
      bucket.total++;
      if (pass) bucket.pass++;
    }
  }
  assert.deepEqual(record.summary, scores);
  console.log(stage, record.revision.slice(0, 7), JSON.stringify(scores));
}
