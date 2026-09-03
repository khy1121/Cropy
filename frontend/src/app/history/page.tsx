"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchHistory } from "@/lib/api";
import type { DiagnosisSummary } from "@/types/diagnosis";

export default function HistoryPage() {
  const [items, setItems] = useState<DiagnosisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory()
      .then((data) => setItems(data.items))
      .catch((err) => setError(err instanceof Error ? err.message : "이력을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <section className="mb-5">
        <h1 className="text-[1.4375rem] font-extrabold leading-snug tracking-tight text-ink">진단 이력</h1>
      </section>

      {loading && <p className="py-10 text-center text-sm text-khaki">불러오는 중…</p>}

      {error && !loading && (
        <p className="rounded-card bg-signal-high-tint px-4 py-3 text-sm font-medium text-signal-high-ink">{error}</p>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="rounded-card border border-line bg-surface p-8 text-center shadow-card">
          <span aria-hidden className="icon-[lucide--wheat] mx-auto mb-3 block h-10 w-10 text-khaki" />
          <p className="text-lg font-bold text-ink">아직 진단 기록이 없어요</p>
          <p className="mt-1 text-sm text-muted">첫 작물을 촬영하면 여기에 이력이 쌓입니다.</p>
          <Link
            href="/"
            className="mt-4 inline-flex rounded-xl bg-brand px-5 py-2.5 text-sm font-bold text-ink transition hover:bg-brand-deep"
          >
            진단 시작
          </Link>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <ul className="grid gap-3 md:grid-cols-2">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                href={`/history/${item.id}`}
                className="flex items-center gap-3.5 rounded-card border border-line bg-surface p-3 shadow-card transition hover:border-brand/40"
              >
                {item.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={item.image_url} alt="" className="h-16 w-16 shrink-0 rounded-xl object-cover" />
                ) : (
                  <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-brand-tint text-brown">
                    <span className="icon-[lucide--leaf] h-7 w-7" />
                  </span>
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-base font-bold text-ink">{item.disease_name}</p>
                  <p className="mt-1 truncate text-xs text-khaki tnum">
                    {item.crop_type && `${item.crop_type} · `}
                    {Math.round(item.confidence * 100)}% ·{" "}
                    {new Date(item.created_at).toLocaleString("ko-KR", {
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                <span aria-hidden className="icon-[lucide--chevron-right] h-5 w-5 shrink-0 text-khaki/60" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
