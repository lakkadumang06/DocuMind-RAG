import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // "standalone" produces a minimal server bundle for the Docker image.
  output: "standalone",
};

export default nextConfig;
