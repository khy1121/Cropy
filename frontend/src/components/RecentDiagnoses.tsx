"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchHistory } from "@/lib/api";
import type { DiagnosisSummary } from "@/types/diagnosis";
import { LeafIllustration } from "./LeafIllustration";

function formatDay(iso: string) {
  return new Date(iso).toLocaleDateString("ko-KR", { month: "long", day: "numeric" });
}

/** 홈 하단의 "최근 진단" 두 줄. 기록이 없으면 아무것도 그리지 않는다(빈 카드 금지). */
export function RecentDiagnoses() {
  const [items, setItems] = useState<DiagnosisSummary[] | null>(null);

  useEffect(() => {
    fetchHistory(1, 2)
      .then((d) => setItems(d.items))
      .catch(() => setItems([]));
  }, []);

  if (!items || items.length === 0) return null;

  return (
    <section>
      <div className="flex items-center justify-between pb-1">
        <h2 className="text-base font-bold text-ink">최근 진단</h2>
        <Link href="/history" className="text-sm font-semibold text-khaki hover:text-ink">
          전체 보기
        </Link>
      </div>
      <ul>
        {items.map((item) => (
          <li key={item.id} className="border-b border-line last:border-b-0">
            <Link href={`/history/${item.id}`} className="flex items-center gap-3.5 py-3">
              <span className="relative h-[3.25rem] w-[3.25rem] shrink-0 overflow-hidden rounded-xl bg-photo-leaf-light">
                {item.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={item.image_url} alt="" className="h-full w-full object-cover" />
                ) : (
                  <LeafIllustration className="absolute -left-1 -top-0.5 h-16 w-16" />
                )}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-base font-bold text-ink">{item.disease_name}</span>
                <span className="block text-sm text-khaki tnum">
                  {formatDay(item.created_at)}, 확신 {Math.round(item.confidence * 100)}%
                </span>
              </span>
              <span aria-hidden className="icon-[lucide--chevron-right] h-5 w-5 shrink-0 text-khaki" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
