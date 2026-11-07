import type { NextConfig } from "next";

// PitchVision runs locally (`npm run build && npm start`). Nothing here assumes a hosting platform, so the
// app could be deployed later, but no deployment target is configured or supported today.
const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  eslint: { ignoreDuringBuilds: true }, // type safety comes from `npm run typecheck`
};

export default nextConfig;
