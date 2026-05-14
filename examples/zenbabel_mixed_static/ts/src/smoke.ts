import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const workDir = mkdtempSync(join(tmpdir(), "zenbabel-smoke-"));
const inputPath = join(workDir, "records.json");
const outputPath = join(workDir, "output.json");
const manifestPath = join(workDir, "manifest.json");

writeFileSync(
  inputPath,
  JSON.stringify([
    { id: "order-001", feature: 0.12, segment: "small" },
    { id: "order-002", feature: 0.71, segment: "enterprise" }
  ]),
  "utf8"
);

writeFileSync(
  manifestPath,
  JSON.stringify({
    protocol: "zenml-portable-json-v1",
    step_name: "score_or_transform",
    source_identity:
      "examples/zenbabel_mixed_static/ts/src/steps/score_or_transform.ts#scoreOrTransform",
    parameters: { threshold: 0.64 },
    inputs: { records: inputPath },
    outputs: { output: outputPath }
  }),
  "utf8"
);

process.env.ZENML_PORTABLE_STEP_MANIFEST = manifestPath;
await import("./steps/score_or_transform.js");

const output = JSON.parse(readFileSync(outputPath, "utf8"));
if (output.metadata.accepted_count !== 1) {
  throw new Error(
    `Expected one accepted record, got ${output.metadata.accepted_count}.`
  );
}

console.log(`Smoke test wrote portable output to ${outputPath}`);
