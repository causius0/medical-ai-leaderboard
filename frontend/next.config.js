/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  basePath: "/medical-ai-leaderboard",
  assetPrefix: "/medical-ai-leaderboard/",
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

module.exports = nextConfig;
