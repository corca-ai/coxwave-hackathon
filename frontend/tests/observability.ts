import fs from "node:fs";
import path from "node:path";

const ARTIFACT_DIR = path.resolve(process.cwd(), "tests/_artifacts");

export function writeArtifact(filename: string, content: string): string {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  const target = path.join(ARTIFACT_DIR, filename);
  fs.writeFileSync(target, content, "utf-8");
  return target;
}

export function writeJsonArtifact(filename: string, data: unknown): string {
  const content = JSON.stringify(data, null, 2);
  return writeArtifact(filename, content);
}
