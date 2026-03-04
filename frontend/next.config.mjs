/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy API calls to the backend during development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/:path*`,
      },
    ];
  },

  // Standalone output for Docker deployment
  output: 'standalone',

  // Disable strict mode double-renders in dev for SSE/WS
  reactStrictMode: false,

  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
      },
    ],
  },
};

export default nextConfig;
