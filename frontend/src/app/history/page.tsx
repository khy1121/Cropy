"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { fetchHistory } from "@/lib/api";
import type { DiagnosisSummary } from "@/types/diagnosis";
import { LeafIllustration } from "@/components/LeafIllustration";

const DAY = ["일", "월", "화", "수", "목", "금", "토"];

function summarize(items: DiagnosisSummary[]) {
  const year = new Date().getFullYear();
  const thisYear = items.filter((i) => new Date(i.created_at).getFullYear() === year);
  if (thisYear.length === 0) return null;
  const count = new Map<string, number>();
  for (const i of thisYear) count.set(i.disease_name, (count.get(i.disease_name) ?? 0) + 1);
  const [top] = [...count.entries()].sort((x, y) => y[1] - x[1]);
  return thisYear.length >= 2 && top[1] >= 2
    ? `올해 ${thisYear.length}번 진단했고, ${top[0]}이 가장 많았어요`
    : `올해 ${thisYear.length}번 진단했어요`;
}

export default function HistoryPage() {
  const [items, setItems] = useState<DiagnosisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory(1, 50)
      .then((data) => setItems(data.items))
      .catch((err) => setError(err instanceof Error ? err.message : "이력을 불러오지 못했어요."))
      .finally(() => setLoading(false));
  }, []);

  // 월별 묶음 (최신순)
  const groups = useMemo(() => {
    const map = new Map<string, DiagnosisSummary[]>();
    for (const it of items) {
      const d = new Date(it.created_at);
      const key = `${d.getFullYear()}-${d.getMonth()}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(it);
    }
    return [...map.entries()].map(([key, list]) => {
      const [y, m] = key.split("-").map(Number);
      const label = y === new Date().getFullYear() ? `${m + 1}월` : `${y}년 ${m + 1}월`;
      return { key, label, list };
    });
  }, [items]);

  const summary = summarize(items);

  return (
    <div>
      <h1 className="sr-only">진단 이력</h1>
      {summary && <p className="text-base font-medium text-khaki tnum">{summary}</p>}

      {loading && (
        <ul className="mt-6 space-y-4" aria-label="불러오는 중">
          {[0, 1, 2].map((i) => (
            <li key={i} className="flex animate-pulse items-center gap-3.5">
              <span className="h-[3.75rem] w-[3.75rem] rounded-2xl bg-khaki-tint" />
              <span className="flex-1 space-y-2">
                <span className="block h-4 w-2/5 rounded bg-khaki-tint" />
                <span className="block h-3 w-3/5 rounded bg-khaki-tint" />
              </span>
            </li>
          ))}
        </ul>
      )}

      {error && !loading && (
        <p className="mt-6 rounded-xl bg-signal-high-tint px-4 py-3 text-sm font-semibold text-signal-high-ink">{error}</p>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="flex min-h-[50vh] flex-col items-center justify-center text-center">
          <span aria-hidden className="icon-[lucide--history] h-14 w-14 text-khaki" />
          <p className="mt-4 text-2xl font-extrabold text-ink">아직 진단한 기록이 없어요</p>
          <p className="mt-1.5 text-base text-khaki">잎 사진 한 장이면 병명과 농약을 바로 알려드려요</p>
          <Link
            href="/"
            className="mt-6 inline-flex w-full max-w-xs items-center justify-center rounded-2xl bg-brand py-4 text-base font-bold text-ink shadow-cta"
          >
            첫 진단 시작하기
          </Link>
        </div>
      )}

      {!loading && !error && groups.length > 0 && (
        <div className="mt-5 space-y-6 md:grid md:grid-cols-2 md:gap-x-8 md:space-y-0">
          {groups.map((g) => (
            <section key={g.key}>
              <h2 className="text-sm font-bold text-khaki">{g.label}</h2>
              <ul className="mt-1 divide-y divide-line">
                {g.list.map((item) => {
                  const d = new Date(item.created_at);
                  return (
                    <li key={item.id}>
                      <Link href={`/history/${item.id}`} className="flex items-center gap-3.5 py-3.5">
                        <span className="relative h-[3.75rem] w-[3.75rem] shrink-0 overflow-hidden rounded-2xl bg-photo-leaf-light">
                          {item.image_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={item.image_url} alt="" className="h-full w-full object-cover" />
                          ) : (
                            <LeafIllustration className="absolute -left-1.5 -top-1 h-[4.6rem] w-[4.6rem]" />
                          )}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-base font-bold text-ink">{item.disease_name}</span>
                          <span className="block text-sm text-khaki tnum">
                            {d.getDate()}일 ({DAY[d.getDay()]}), 확신 {Math.round(item.confidence * 100)}%
                            {item.crop_type && `, ${item.crop_type}`}
                          </span>
                        </span>
                        <span aria-hidden className="icon-[lucide--chevron-right] h-5 w-5 shrink-0 text-khaki" />
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
