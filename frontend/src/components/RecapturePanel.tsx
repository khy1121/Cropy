"use client";

import { useRef, useState } from "react";
import { refineDiagnosis } from "@/lib/api";
import type { DiagnoseResponse, PredictionItem, RecaptureGuidance } from "@/types/diagnosis";
import { LeafIllustration } from "./LeafIllustration";

interface Props {
  diagnosisId: string;
  guidance: RecaptureGuidance;
  topPredictions: PredictionItem[];
  onRefined: (result: DiagnoseResponse) => void;
  onSkip: () => void;
}

/** 받침 유무로 목적격 조사를 고른다 ("잎 뒷면" → 을, "잎맥·잎 가장자리" → 를). */
function objectParticle(word: string): string {
  const trimmed = word.trim();
  const last = trimmed.charCodeAt(trimmed.length - 1);
  if (!trimmed || last < 0xac00 || last > 0xd7a3) return "을(를)";
  return (last - 0xac00) % 28 === 0 ? "를" : "을";
}

/**
 * 혼동쌍 재촬영 유도 — 이 앱만의 장면.
 * 두 후보를 한 막대로 견주고, 잎 일러스트에 "어디를 봐야 하는지"를 표시한 뒤 한 가지 행동만 남긴다.
 */
export function RecapturePanel({ diagnosisId, guidance, topPredictions, onRefined, onSkip }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 후보 2개의 확률 — top_predictions에서 이름으로 찾는다
  const pair = guidance.candidates.slice(0, 2).map((c) => ({
    ...c,
    pct: Math.round((topPredictions.find((p) => p.name === c.name)?.confidence ?? 0) * 100),
  }));
  const [a, b] = pair;
  const sum = (a?.pct ?? 0) + (b?.pct ?? 0);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      onRefined(await refineDiagnosis(diagnosisId, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "다시 확인하지 못했어요. 한 번 더 시도해 주세요.");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const region = guidance.region;
  const isBack = region.includes("뒷면");

  return (
    <section className="flex min-h-[calc(100vh-8rem)] flex-col px-5 pt-3 md:min-h-0">
      <p className="flex items-center gap-1.5 text-base font-bold text-ink">
        <span aria-hidden className="icon-[lucide--scan-search] h-5 w-5 text-khaki" />
        한 번만 더 볼게요
      </p>
      <h2 className="mt-4 text-2xl font-black leading-[1.35] tracking-tight text-ink">
        둘 중 하나예요.
        <br />
        {region}
        {objectParticle(region)} 보면 알 수 있어요
      </h2>

      {a && b && sum > 0 && (
        <div className="mt-5 flex h-12 overflow-hidden rounded-xl bg-line text-sm font-bold text-white tnum" role="img" aria-label={`${a.name} ${a.pct}%, ${b.name} ${b.pct}%`}>
          <span className="flex items-center bg-photo-spot pl-3.5" style={{ width: `${a.pct}%` }}>
            <span className="truncate">{a.name} {a.pct}%</span>
          </span>
          <span className="flex items-center bg-photo-leaf pl-3" style={{ width: `${b.pct}%` }}>
            <span className="truncate">{b.name} {b.pct}%</span>
          </span>
        </div>
      )}

      <div className="mt-5 flex flex-col items-center">
        <LeafIllustration variant={isBack ? "back-highlight" : "front"} className="h-52 w-52" />
        <p className="mt-1 flex items-center gap-1.5 text-sm font-bold text-khaki">
          <span aria-hidden className="icon-[lucide--flip-horizontal] h-4 w-4" />
          {guidance.instruction}
        </p>
      </div>

      <ul className="mt-5 space-y-2.5">
        {pair.map((c, i) => (
          <li key={c.name} className="flex items-center gap-2.5 text-base text-ink">
            <span aria-hidden className={`h-3.5 w-3.5 shrink-0 rounded-[3px] ${i === 0 ? "bg-photo-spot" : "bg-photo-leaf"}`} />
            {c.cue}
          </li>
        ))}
      </ul>

      {error && (
        <p className="mt-4 rounded-xl bg-signal-high-tint px-4 py-3 text-sm font-semibold text-signal-high-ink">{error}</p>
      )}

      <div className="mt-auto pb-6 pt-8">
        <label
          htmlFor="recapture-photo"
          aria-disabled={loading}
          className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl bg-brand py-4 text-base font-bold text-ink shadow-cta transition active:scale-[0.99] aria-disabled:opacity-60"
        >
          {loading ? (
            <>
              <span aria-hidden className="icon-[lucide--loader-circle] h-5 w-5 animate-spin" />
              확인하는 중…
            </>
          ) : (
            <>
              <span aria-hidden className="icon-[lucide--camera] h-5 w-5" />
              {region} 찍기
            </>
          )}
          <input
            ref={fileRef}
            id="recapture-photo"
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
            disabled={loading}
            className="hidden"
          />
        </label>
        <button
          type="button"
          onClick={onSkip}
          className="mt-3 w-full text-center text-sm font-semibold text-khaki underline underline-offset-4"
        >
          지금 결과로 볼게요
        </button>
      </div>
    </section>
  );
}
