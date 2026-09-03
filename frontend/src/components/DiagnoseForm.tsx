"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { diagnoseImage } from "@/lib/api";
import { onCaptureRequest, type CaptureMode } from "@/lib/capture";
import type { DiagnoseResponse } from "@/types/diagnosis";
import { DiagnosisResult } from "./DiagnosisResult";
import { RecapturePanel } from "./RecapturePanel";
import { RecentDiagnoses } from "./RecentDiagnoses";
import { LeafIllustration } from "./LeafIllustration";

const CROPS = ["고추", "무", "배추"] as const;

// top-1이 이 아래면 잎이 잘 안 잡힌 사진일 가능성이 높다 — 결과보다 다시 찍기를 먼저 권한다
const LOW_CONFIDENCE = 0.5;

type Stage = "home" | "preview" | "loading" | "result";

export function DiagnoseForm() {
  const searchParams = useSearchParams();
  const cameraRef = useRef<HTMLInputElement>(null);
  const albumRef = useRef<HTMLInputElement>(null);
  const topRef = useRef<HTMLDivElement>(null);

  const [cropType, setCropType] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("home");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DiagnoseResponse | null>(null);
  const [skipRecapture, setSkipRecapture] = useState(false);
  const [acceptLow, setAcceptLow] = useState(false);

  const open = useCallback((mode: CaptureMode) => {
    (mode === "camera" ? cameraRef : albumRef).current?.click();
  }, []);

  // 하단 셔터 바에서 온 요청
  useEffect(() => onCaptureRequest(open), [open]);

  // 홈이 아닌 단계에서는 하단 셔터 바를 숨긴다 (globals.css)
  useEffect(() => {
    document.documentElement.dataset.fullscreen = stage === "home" ? "" : "1";
    return () => {
      document.documentElement.dataset.fullscreen = "";
    };
  }, [stage]);

  // 다른 화면의 셔터를 눌러 /?capture=1 로 왔을 때는 제스처가 끊겨 카메라를 바로 열 수 없다.
  // 대신 촬영 카드로 시선을 옮긴다.
  useEffect(() => {
    if (searchParams.get("capture")) topRef.current?.scrollIntoView({ block: "start" });
  }, [searchParams]);

  const pick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setError(null);
    setSkipRecapture(false);
    setAcceptLow(false);
    setStage("preview");
    e.target.value = "";
  };

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    setStage("home");
  };

  const submit = async () => {
    if (!file) return;
    setStage("loading");
    setError(null);
    try {
      const data = await diagnoseImage(file, cropType || undefined);
      setResult(data);
      setStage("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "진단에 실패했어요. 잠시 후 다시 시도해 주세요.");
      setStage("preview");
    }
  };

  const inputs = (
    <>
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={pick} className="hidden" aria-hidden />
      <input ref={albumRef} type="file" accept="image/*" onChange={pick} className="hidden" aria-hidden />
    </>
  );

  /* ---------- 진단 중 ---------- */
  if (stage === "loading") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center text-center" role="status" aria-live="polite">
        <span aria-hidden className="icon-[lucide--loader-circle] h-14 w-14 animate-spin text-brand" />
        <p className="mt-5 text-2xl font-extrabold text-ink">진단 중…</p>
        <p className="mt-1 text-base text-khaki">잎을 살펴보고 있어요</p>
        {inputs}
      </div>
    );
  }

  /* ---------- 결과 ---------- */
  if (stage === "result" && result) {
    const lowConfidence = result.confidence < LOW_CONFIDENCE && result.category !== "normal" && !acceptLow;
    const showRecapture = Boolean(result.recapture) && !skipRecapture && !lowConfidence;
    return (
      <div className="-mx-5 -mt-5 md:mx-0 md:mt-0">
        {inputs}
        {lowConfidence ? (
          <LowConfidence
            preview={result.image_url ?? preview}
            pct={Math.round(result.confidence * 100)}
            onRetake={() => open("camera")}
            onAccept={() => setAcceptLow(true)}
          />
        ) : showRecapture ? (
          <RecapturePanel
            diagnosisId={result.id}
            guidance={result.recapture!}
            topPredictions={result.top_predictions}
            onRefined={(r) => {
              setResult(r);
              setSkipRecapture(true);
            }}
            onSkip={() => setSkipRecapture(true)}
          />
        ) : (
          <DiagnosisResult result={result} onNew={reset} />
        )}
      </div>
    );
  }

  /* ---------- 사진 확인 ---------- */
  if (stage === "preview" && preview) {
    return (
      <div className="-mx-5 -mt-5 flex min-h-[calc(100vh-8rem)] flex-col bg-photo-deep text-white md:mx-0 md:mt-0 md:min-h-0 md:rounded-card">
        {inputs}
        <div className="flex items-center justify-between px-5 pt-4">
          <button type="button" onClick={reset} aria-label="취소" className="flex h-11 w-11 items-center justify-center rounded-full">
            <span aria-hidden className="icon-[lucide--x] h-6 w-6" />
          </button>
          <CropPicker value={cropType} onChange={setCropType} dark />
          <span className="w-11" />
        </div>
        <div className="relative mx-5 mt-3 min-h-[24rem] flex-1 overflow-hidden rounded-[2rem] bg-photo-leaf/60">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="촬영한 잎" className="absolute inset-0 h-full w-full object-cover" />
        </div>
        {error && (
          <p className="mx-5 mt-3 rounded-xl bg-signal-high-tint px-4 py-3 text-sm font-semibold text-signal-high-ink">{error}</p>
        )}
        <div className="flex gap-3 px-5 pb-6 pt-4">
          <button
            type="button"
            onClick={() => open("camera")}
            className="flex-1 rounded-2xl border border-white/30 py-4 text-base font-bold text-white transition active:scale-[0.99]"
          >
            다시 찍기
          </button>
          <button
            type="button"
            onClick={submit}
            className="flex-1 rounded-2xl bg-brand py-4 text-base font-bold text-ink shadow-cta transition active:scale-[0.99]"
          >
            진단하기
          </button>
        </div>
      </div>
    );
  }

  /* ---------- 홈 ---------- */
  return (
    <div ref={topRef} className="space-y-8 scroll-mt-20">
      {inputs}
      <section>
        <h1 className="text-[1.75rem] font-black leading-[1.3] tracking-tight text-ink md:text-[2rem]">
          잎을 찍으면
          <br />
          병과 약을 알려드려요
        </h1>
        <p className="mt-2 text-base font-medium text-khaki">고추, 무, 배추 잎을 진단할 수 있어요</p>
      </section>

      <CropPicker value={cropType} onChange={setCropType} />

      <button
        type="button"
        onClick={() => open("camera")}
        className="hidden w-full items-center justify-center gap-2 rounded-2xl bg-brand py-4 text-base font-bold text-ink shadow-cta transition hover:bg-brand-deep md:flex"
      >
        <span aria-hidden className="icon-[lucide--camera] h-5 w-5" />
        잎 사진 찍기
      </button>

      <RecentDiagnoses />
    </div>
  );
}

/** 작물 타일. 다시 누르면 해제되어 자동 감지로 돌아간다. */
function CropPicker({ value, onChange, dark = false }: { value: string; onChange: (v: string) => void; dark?: boolean }) {
  if (dark) {
    return (
      <div role="group" aria-label="작물" className="flex gap-1.5 rounded-full bg-photo-scrim/85 p-1">
        {CROPS.map((c) => (
          <button
            key={c}
            type="button"
            aria-pressed={value === c}
            onClick={() => onChange(value === c ? "" : c)}
            className={`rounded-full px-3.5 py-2 text-sm font-bold transition ${value === c ? "bg-brand text-ink" : "text-white/85"}`}
          >
            {c}
          </button>
        ))}
      </div>
    );
  }
  return (
    <div role="group" aria-label="작물 선택" className="grid grid-cols-3 gap-3">
      {CROPS.map((c) => {
        const on = value === c;
        return (
          <button
            key={c}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(on ? "" : c)}
            className={`flex flex-col items-center gap-2 rounded-[1.25rem] border pb-3.5 pt-4 transition active:scale-[0.98] ${
              on ? "border-brand bg-brand-tint ring-1 ring-brand" : "border-line bg-surface hover:border-brand/50"
            }`}
          >
            <LeafIllustration className="h-14 w-14" />
            <span className="text-base font-bold text-ink">{c}</span>
          </button>
        );
      })}
    </div>
  );
}

/** 잎이 잘 안 잡힌 사진 — 결과 대신 다시 찍기를 먼저 권한다. */
function LowConfidence({ preview, pct, onRetake, onAccept }: { preview: string | null; pct: number; onRetake: () => void; onAccept: () => void }) {
  return (
    <div className="px-5 pt-5">
      {preview && (
        <div className="overflow-hidden rounded-[1.5rem] bg-photo-leaf-light">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="촬영한 잎" className="h-48 w-full object-cover" />
        </div>
      )}
      <section className="mt-4 rounded-[1.25rem] border border-brand bg-brand-tint p-4">
        <div className="flex items-center gap-2">
          <span aria-hidden className="icon-[lucide--triangle-alert] h-6 w-6 text-signal-med-ink" />
          <h2 className="text-2xl font-extrabold text-ink">잎이 잘 안 보여요</h2>
        </div>
        <p className="mt-2 text-base leading-relaxed text-ink">
          사진에서 잎을 찾기 어려워 확신이 낮아요(확신 {pct}%). 잎 한 장이 화면에 꽉 차게, 그늘에서 다시 찍어주세요.
        </p>
        <button
          type="button"
          onClick={onRetake}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-brand py-4 text-base font-bold text-ink shadow-cta"
        >
          <span aria-hidden className="icon-[lucide--camera] h-5 w-5" />
          다시 찍기
        </button>
        <button type="button" onClick={onAccept} className="mt-3 w-full text-center text-sm font-semibold text-khaki underline underline-offset-4">
          이 결과 그대로 보기
        </button>
      </section>
    </div>
  );
}
