import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  outputFileTracingRoot: "/Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/frontend",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "res.cloudinary.com",
      },
    ],
  },
  // Proxy /api/* to backend — avoids CORS in all environments
  async rewrites() {
    const backend =
      process.env.BACKEND_URL ?? "https://lms-api-ukhs.onrender.com";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
