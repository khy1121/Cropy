"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { TextSizeToggle } from "./TextSizeToggle";

const NAV = [
  { href: "/", label: "진단", match: (p: string) => p === "/" },
  { href: "/history", label: "이력", match: (p: string) => p.startsWith("/history") },
];

/**
 * 상단 바. 홈은 워드마크만, 하위 화면은 뒤로가기 + 제목.
 * 큰글씨 토글은 어디서나 같은 자리에 둔다(어르신이 한 번 찾으면 계속 찾을 수 있게).
 */
export function AppBar() {
  const pathname = usePathname();
  const isDetail = /^\/history\/.+/.test(pathname);
  const title = pathname.startsWith("/history") ? (isDetail ? "진단 기록" : "진단 이력") : null;

  return (
    <header className="sticky top-0 z-20 bg-paper/90 pt-[env(safe-area-inset-top)] backdrop-blur">
      <div className="flex items-center gap-2 px-5 py-3 md:px-8">
        {title ? (
          <div className="flex items-center gap-1.5">
            {isDetail && (
              <Link
                href="/history"
                aria-label="이력 목록으로"
                className="-ml-2 flex h-11 w-11 items-center justify-center rounded-full text-ink transition hover:bg-khaki-tint"
              >
                <span aria-hidden className="icon-[lucide--chevron-left] h-6 w-6" />
              </Link>
            )}
            <span className="text-lg font-extrabold tracking-tight text-ink">{title}</span>
          </div>
        ) : (
          <Link href="/" className="text-xl font-black tracking-tight text-ink">
            CropCare
          </Link>
        )}

        <div className="ml-auto flex items-center gap-2">
          <TextSizeToggle />
          <nav className="hidden items-center gap-1.5 md:flex">
            {NAV.map((item) => {
              const active = item.match(pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-full px-4 py-2 text-sm font-bold transition-colors ${
                    active ? "bg-brand-tint text-ink" : "text-muted hover:bg-khaki-tint hover:text-ink"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
