"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { TextSizeToggle } from "./TextSizeToggle";

const NAV = [
  { href: "/", label: "진단", match: (p: string) => p === "/" },
  { href: "/history", label: "이력", match: (p: string) => p.startsWith("/history") },
];

export function AppBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-paper/85 pt-[env(safe-area-inset-top)] backdrop-blur">
      <div className="flex items-center gap-2.5 px-5 py-3.5 md:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <span
            aria-hidden
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-tint text-brown"
          >
            <span className="icon-[lucide--sprout] h-5 w-5" />
          </span>
          <span className="leading-none">
            <span className="block text-lg font-extrabold tracking-tight text-ink">CropCare</span>
            <span className="mt-0.5 block text-xs font-medium text-khaki">현장 병해충 진단</span>
          </span>
        </Link>

        {/* 큰글씨 토글은 화면 폭과 무관하게 항상 보여야 한다 (모바일에서 하단 탭이
            네비게이션을 가져가도 이 버튼은 앱바에 남는다) */}
        <div className="ml-auto flex items-center gap-2">
          <TextSizeToggle />

          {/* Desktop nav — bottom tabs take over below md */}
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
