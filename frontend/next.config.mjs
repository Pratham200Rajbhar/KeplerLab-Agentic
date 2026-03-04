/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy API calls to the backend during development
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/presentation/slides/:path*',
        destination: `${backendUrl}/presentation/slides/:path*`,
      },
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
      },
    ];
  },

  // Standalone output for Docker deployment
  output: 'standalone',

  // Enable React Strict Mode for catching bugs early
  reactStrictMode: true,

  images: {
    remotePatterns: [
      {
        protocol: process.env.NEXT_PUBLIC_API_PROTOCOL || 'http',
        hostname: process.env.NEXT_PUBLIC_API_HOST || 'localhost',
        port: process.env.NEXT_PUBLIC_API_PORT || '8000',
      },
      {
        protocol: 'https',
        hostname: process.env.NEXT_PUBLIC_API_HOST || 'localhost',
      },
    ],
  },
};

export default nextConfig;
