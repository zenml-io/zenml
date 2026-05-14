import { readFileSync, writeFileSync } from "node:fs";

const MANIFEST_ENV_VAR = "ZENML_PORTABLE_STEP_MANIFEST";

export type PortableManifest = {
  protocol: "zenml-portable-json-v1";
  step_name: string;
  source_identity?: string;
  parameters: Record<string, unknown>;
  inputs: Record<string, string>;
  outputs: Record<string, string>;
};

export function readManifestFromEnvironment(): PortableManifest {
  const manifestPath = process.env[MANIFEST_ENV_VAR];
  if (!manifestPath) {
    throw new Error(`Missing ${MANIFEST_ENV_VAR} environment variable.`);
  }

  const manifest = readJsonFile<PortableManifest>(manifestPath);
  if (manifest.protocol !== "zenml-portable-json-v1") {
    throw new Error(
      `Unsupported portable protocol ${JSON.stringify(manifest.protocol)}.`
    );
  }

  return manifest;
}

export function readInput<T>(manifest: PortableManifest, name: string): T {
  const inputPath = manifest.inputs[name];
  if (!inputPath) {
    throw new Error(
      `Portable manifest for step ${manifest.step_name} has no input ${name}.`
    );
  }

  return readJsonFile<T>(inputPath);
}

export function writeOutput(
  manifest: PortableManifest,
  name: string,
  value: unknown
): void {
  const outputPath = manifest.outputs[name];
  if (!outputPath) {
    throw new Error(
      `Portable manifest for step ${manifest.step_name} has no output ${name}.`
    );
  }

  writeFileSync(outputPath, JSON.stringify(value, null, 2), "utf8");
}

function readJsonFile<T>(path: string): T {
  try {
    return JSON.parse(readFileSync(path, "utf8")) as T;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to read JSON file ${path}: ${message}`);
  }
}
