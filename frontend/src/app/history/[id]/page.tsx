"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchDiagnosisDetail } from "@/lib/api";
import type { DiagnoseResponse } from "@/types/diagnosis";
import { DiagnosisResult } from "@/components/DiagnosisResult";

export default function HistoryDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [result, setResult] = useState<DiagnoseResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 결과 화면은 자체 고정 CTA를 쓰므로 하단 바를 숨긴다
  useEffect(() => {
    document.documentElement.dataset.fullscreen = "1";
    return () => {
      document.documentElement.dataset.fullscreen = "";
    };
  }, []);

  useEffect(() => {
    fetchDiagnosisDetail(id)
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "기록을 불러오지 못했어요."))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="-mx-5 -mt-5 md:mx-auto md:mt-0 md:w-full md:max-w-2xl">
      {loading && (
        <div className="animate-pulse">
          <div className="h-72 bg-khaki-tint" />
          <div className="space-y-3 px-5 pt-6">
            <div className="h-8 w-1/2 rounded bg-khaki-tint" />
            <div className="h-4 w-2/3 rounded bg-khaki-tint" />
          </div>
        </div>
      )}
      {(error || (!loading && !result)) && (
        <p className="mx-5 mt-5 rounded-xl bg-signal-high-tint px-4 py-3 text-sm font-semibold text-signal-high-ink">
          {error || "그 기록을 찾을 수 없어요."}
        </p>
      )}
      {result && <DiagnosisResult result={result} />}
    </div>
  );
}
