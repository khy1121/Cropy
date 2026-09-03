"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchDiagnosisDetail } from "@/lib/api";
import type { DiagnoseResponse } from "@/types/diagnosis";
import { DiagnosisResult } from "@/components/DiagnosisResult";

export default function HistoryDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [result, setResult] = useState<DiagnoseResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDiagnosisDetail(id)
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "기록을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="mx-auto w-full max-w-2xl">
      <Link
        href="/history"
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-muted transition hover:text-ink"
      >
        <span aria-hidden className="icon-[lucide--chevron-left] h-4 w-4" />
        이력 목록
      </Link>

      {loading && <p className="py-10 text-center text-sm text-khaki">불러오는 중…</p>}
      {(error || (!loading && !result)) && (
        <p className="rounded-card bg-signal-high-tint px-4 py-3 text-sm font-medium text-signal-high-ink">
          {error || "해당 기록을 찾을 수 없습니다."}
        </p>
      )}
      {result && <DiagnosisResult result={result} />}
    </div>
  );
}
