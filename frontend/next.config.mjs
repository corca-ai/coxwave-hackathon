import fs from "node:fs";
import path from "node:path";
import dotenv from "dotenv";

const rootEnv = path.resolve(process.cwd(), "..", ".env");
if (fs.existsSync(rootEnv)) {
  dotenv.config({ path: rootEnv });
}

const nextConfig = {
  reactStrictMode: true,
  experimental: {
    optimizePackageImports: ["@xyflow/react"]
  }
};

export default nextConfig;
