import path from "node:path";
import dotenv from "dotenv";
import { defineConfig } from "vitest/config";

dotenv.config({ path: path.resolve(process.cwd(), "..", ".env") });

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.ts"]
  }
});
