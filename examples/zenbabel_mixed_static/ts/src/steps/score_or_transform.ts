import {
  readInput,
  readManifestFromEnvironment,
  writeOutput,
} from "../portable.js";

type InputRecord = {
  id: string;
  feature: number;
  segment: string;
};

type ScoredRecord = InputRecord & {
  score: number;
  label: "accept" | "review";
};

type ScoredBundle = {
  records: ScoredRecord[];
  metadata: {
    threshold: number;
    accepted_count: number;
    total_count: number;
  };
};

export function scoreOrTransform(
  records: InputRecord[],
  parameters: Record<string, unknown>
): ScoredBundle {
  const threshold = readNumberParameter(parameters, "threshold", 0.64);
  const scoredRecords: ScoredRecord[] = records.map((record) => {
    const segmentBoost = record.segment === "enterprise" ? 0.18 : 0.04;
    const score = clamp(round(record.feature + segmentBoost));
    const label: ScoredRecord["label"] =
      score >= threshold ? "accept" : "review";
    return {
      ...record,
      score,
      label,
    };
  });
  const acceptedCount = scoredRecords.filter(
    (record) => record.label === "accept"
  ).length;

  return {
    records: scoredRecords,
    metadata: {
      threshold,
      accepted_count: acceptedCount,
      total_count: scoredRecords.length,
    },
  };
}

function readNumberParameter(
  parameters: Record<string, unknown>,
  name: string,
  fallback: number
): number {
  const value = parameters[name];
  if (value === undefined) {
    return fallback;
  }
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Parameter ${name} must be a finite number.`);
  }
  return value;
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function clamp(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function main(): void {
  const manifest = readManifestFromEnvironment();
  const records = readInput<InputRecord[]>(manifest, "records");
  const output = scoreOrTransform(records, manifest.parameters);
  writeOutput(manifest, "output", output);
}

main();
