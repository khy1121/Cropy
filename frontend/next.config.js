/** @type {import('next').NextConfig} */

// 127.0.0.1을 명시한다. Node는 "localhost"를 ::1(IPv6)로 먼저 해석하는데,
// uvicorn은 기본적으로 IPv4에만 바인딩하므로 rewrite가 ECONNREFUSED로 실패한다.
const BACKEND = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000";

const nextConfig = {
  // Docker 배포용 최소 실행본(server.js + 필요한 node_modules만)을 생성한다.
  // 로컬 `next dev`/`next start`에는 영향이 없다.
  output: "standalone",

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND}/api/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${BACKEND}/uploads/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
