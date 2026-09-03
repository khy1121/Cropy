"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { requestCapture } from "@/lib/capture";

/**
 * 하단 바.
 *
 * 홈에서는 카메라 앱처럼 "앨범 · 찍기 · 이력" 셔터 바가 되고, 다른 화면에서는
 * "진단 · 이력" 탭이 된다. 셔터는 이 앱의 단 하나의 주 행동이라 화면 어디서든
 * 가운데 큰 노란 버튼으로 고정한다.
 */
export function BottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const isHome = pathname === "/";
  const onHistory = pathname.startsWith("/history");

  const shoot = () => {
    if (isHome) requestCapture("camera");
    else router.push("/?capture=1");
  };
  const album = () => {
    if (isHome) requestCapture("album");
    else router.push("/");
  };

  return (
    <nav className="bottom-nav fixed inset-x-0 bottom-0 z-20 md:hidden">
      <div className="mx-auto flex max-w-app items-end justify-between bg-paper/95 px-10 pb-2 pt-2 backdrop-blur">
        {isHome ? (
          <button type="button" onClick={album} className="flex min-w-14 flex-col items-center gap-1 py-1 text-xs font-bold text-khaki">
            <span aria-hidden className="icon-[lucide--image] h-6 w-6" />
            앨범
          </button>
        ) : (
          <Link
            href="/"
            className={`flex min-w-14 flex-col items-center gap-1 py-1 text-xs font-bold ${!onHistory ? "text-ink" : "text-khaki"}`}
          >
            <span aria-hidden className="icon-[lucide--leaf] h-6 w-6" />
            진단
          </Link>
        )}

        <button
          type="button"
          onClick={shoot}
          aria-label="잎 사진 찍기"
          className="-mt-6 flex flex-col items-center gap-1.5"
        >
          <span className="flex h-[4.5rem] w-[4.5rem] items-center justify-center rounded-full bg-brand text-ink shadow-shutter ring-[3px] ring-ink transition active:scale-95">
            <span aria-hidden className="icon-[lucide--camera] h-8 w-8" />
          </span>
          <span className="text-xs font-bold text-ink">찍기</span>
        </button>

        <Link
          href="/history"
          aria-current={onHistory ? "page" : undefined}
          className={`flex min-w-14 flex-col items-center gap-1 py-1 text-xs font-bold ${onHistory ? "text-ink" : "text-khaki"}`}
        >
          <span aria-hidden className="icon-[lucide--history] h-6 w-6" />
          이력
        </Link>
      </div>
      <div className="bg-paper/95 pb-[env(safe-area-inset-bottom)]" />
    </nav>
  );
}
