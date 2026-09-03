"use client";

import { useRef, useState } from "react";
import { refineDiagnosis } from "@/lib/api";
import type { DiagnoseResponse, RecaptureGuidance } from "@/types/diagnosis";

interface Props {
  diagnosisId: string;
  guidance: RecaptureGuidance;
  onRefined: (result: DiagnoseResponse) => void;
}

/** 받침 유무로 목적격 조사를 고른다 ("잎 뒷면" → 을, "잎맥·잎 가장자리" → 를). */
function objectParticle(word: string): string {
  const trimmed = word.trim();
  const last = trimmed.charCodeAt(trimmed.length - 1);
  if (!trimmed || last < 0xac00 || last > 0xd7a3) return "을(를)";
  return (last - 0xac00) % 28 === 0 ? "를" : "을";
}

export function RecapturePanel({ diagnosisId, guidance, onRefined }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const refined = await refineDiagnosis(diagnosisId, file);
      onRefined(refined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "재확정에 실패했어요. 다시 시도해 주세요.");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <section className="rounded-card border border-signal-med/30 bg-signal-med-tint p-5">
      <div className="flex items-center gap-2">
        <span aria-hidden className="icon-[lucide--scan-search] h-5 w-5 text-signal-med-ink" />
        <h3 className="text-base font-extrabold text-ink">한 장 더 찍어볼까요?</h3>
      </div>
      <p className="mt-1.5 text-sm leading-relaxed text-ink/80">
        두 병해가 비슷해 보여요. <b className="font-bold">{guidance.region}</b>
        {objectParticle(guidance.region)} 찍으면 구분하는 데 도움이 돼요.
      </p>

      <p className="mt-3 rounded-xl bg-surface/70 px-3.5 py-2.5 text-sm font-semibold text-ink">
        {guidance.instruction}
      </p>

      {guidance.candidates.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {guidance.candidates.map((c) => (
            <li key={c.name} className="flex gap-2 text-xs leading-relaxed text-ink/75">
              <span aria-hidden className="icon-[lucide--corner-down-right] mt-0.5 h-3.5 w-3.5 shrink-0 text-signal-med-ink" />
              <span>{c.cue}</span>
            </li>
          ))}
        </ul>
      )}

      {error && (
        <p className="mt-3 rounded-xl bg-signal-high-tint px-3.5 py-2.5 text-sm font-medium text-signal-high-ink">
          {error}
        </p>
      )}

      <label
        htmlFor="recapture-photo"
        className="mt-4 flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl bg-brand py-3.5 text-base font-bold text-ink shadow-cta transition active:scale-[0.99] hover:bg-brand-deep aria-disabled:opacity-60"
        aria-disabled={loading}
      >
        {loading ? (
          <>
            <span aria-hidden className="icon-[lucide--loader-circle] h-5 w-5 animate-spin" />
            분석 중…
          </>
        ) : (
          <>
            <span aria-hidden className="icon-[lucide--camera] h-5 w-5" />
            {guidance.region} 촬영하기
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
    </section>
  );
}
