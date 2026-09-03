import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppBar } from "@/components/AppBar";
import { BottomNav } from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "CropCare AI",
  description: "AI 기반 농작물 병해충 진단 및 스마트 방제 지원 플랫폼",
  appleWebApp: { capable: true, title: "CropCare", statusBarStyle: "default" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#FAF7F0",
  width: "device-width",
  initialScale: 1,
  // safe-area env() values only resolve with viewport-fit=cover (notch/home-bar devices)
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // 아래 인라인 스크립트가 하이드레이션 전에 data-textsize를 붙이므로
    // 서버 HTML과 달라진다. 이 요소의 속성 차이만 경고에서 제외한다.
    <html lang="ko" suppressHydrationWarning>
      <head>
        {/* 저장된 큰글씨 설정을 첫 페인트 전에 적용한다.
            React 하이드레이션을 기다리면 글씨가 작았다 커지며 깜빡인다. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{if(localStorage.getItem('cropcare:textsize')==='large')" +
              "document.documentElement.dataset.textsize='large'}catch(e){}",
          }}
        />
      </head>
      <body>
        <div className="mx-auto flex min-h-screen w-full max-w-app flex-col bg-paper shadow-[0_0_60px_-30px_rgba(28,43,34,0.25)] md:max-w-3xl md:shadow-none lg:max-w-5xl">
          <AppBar />
          <main className="flex-1 px-5 pb-28 pt-5 md:px-8 md:pb-16 md:pt-8">{children}</main>
          <BottomNav />
        </div>
      </body>
    </html>
  );
}
