const serverApiUrl = process.env.SERVER_API_URL ?? 'http://backend:8888';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${serverApiUrl}/api/v1/:path*`,
      },
      {
        source: '/uploads/:path*',
        destination: `${serverApiUrl}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
