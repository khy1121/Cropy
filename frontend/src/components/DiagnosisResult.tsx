import Link from "next/link";
import type { DiagnoseResponse, Severity } from "@/types/diagnosis";
import { LeafIllustration } from "./LeafIllustration";

interface Props {
  result: DiagnoseResponse;
  /** 홈에서 진단했을 때: 새 진단으로 초기화. 이력 상세에서는 생략(홈 링크로 대체). */
  onNew?: () => void;
}

// 심각도는 등급명이 아니라 "지금 무엇을 해야 하는지"로 읽는다
const SEVERITY: Record<Severity, { text: string; cls: string; dot: string }> = {
  high: { text: "빨리 방제해야 해요", cls: "text-signal-high-ink", dot: "bg-signal-high" },
  medium: { text: "며칠 안에 방제하세요", cls: "text-signal-med-ink", dot: "bg-signal-med" },
  low: { text: "지켜보며 관리하세요", cls: "text-signal-low-ink", dot: "bg-signal-low" },
};

const LOW_CONFIDENCE = 0.5;

function Hairline() {
  return <hr className="border-line" />;
}

function SectionTitle({ icon, children }: { icon: string; children: React.ReactNode }) {
  return (
    <h3 className="flex items-center gap-2 text-base font-bold text-ink">
      <span aria-hidden className={`${icon} h-5 w-5 text-khaki`} />
      {children}
    </h3>
  );
}

export function DiagnosisResult({ result, onNew }: Props) {
  const healthy = result.category === "normal";
  const sev = SEVERITY[result.severity ?? "medium"];
  const pct = Math.round(result.confidence * 100);
  const filled = Math.round(result.confidence * 10);
  const refined = Boolean(result.image_url && result.refined_image_url);
  const uncertain = result.confidence < LOW_CONFIDENCE;
  const others = result.top_predictions.slice(1, 3);

  return (
    <article className="md:overflow-hidden md:rounded-card md:border md:border-line md:bg-surface md:shadow-card">
      {/* 사진 — 화면 상단을 차지하고 그 위로 시트가 올라온다 */}
      <div className="relative h-72 overflow-hidden bg-photo-leaf-light md:h-80">
        {result.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={result.image_url} alt="진단한 잎" className="h-full w-full object-cover" />
        ) : (
          <LeafIllustration className="absolute left-1/2 top-2 h-72 w-72 -translate-x-1/2" />
        )}
        {refined && (
          <figure className="absolute bottom-10 right-4 w-24 overflow-hidden rounded-xl border-2 border-white bg-photo-leaf-light shadow-card">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={result.refined_image_url!} alt="판별부위를 다시 찍은 사진" className="h-20 w-full object-cover" />
            <figcaption className="bg-white px-1.5 py-0.5 text-center text-[0.7rem] font-bold text-brown-deep">뒷면 사진</figcaption>
          </figure>
        )}
      </div>

      <div className="relative -mt-7 rounded-t-[1.75rem] bg-surface px-5 pb-32 pt-3 shadow-sheet md:-mt-0 md:rounded-none md:pb-6 md:shadow-none">
        <span aria-hidden className="mx-auto block h-1.5 w-11 rounded-full bg-line md:hidden" />

        {/* 병명 · 확신 · 행동 */}
        <header className="mt-4">
          <h2 className="text-[1.875rem] font-black leading-[1.2] tracking-tight text-ink">{result.disease_name}</h2>
          <p className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-base font-bold">
            <span className="text-ink tnum">확신 {pct}%</span>
            {healthy ? (
              <span className="flex items-center gap-1.5 text-signal-low-ink">
                <span aria-hidden className="h-2 w-2 rounded-full bg-signal-low" />
                건강해요, 이대로 관리하세요
              </span>
            ) : (
              <span className={`flex items-center gap-1.5 ${sev.cls}`}>
                <span aria-hidden className={`h-2 w-2 rounded-full ${sev.dot}`} />
                {sev.text}
              </span>
            )}
          </p>
          <div className="mt-2.5 grid grid-cols-10 gap-1" aria-hidden>
            {Array.from({ length: 10 }, (_, i) => (
              <span key={i} className={`h-1.5 rounded-full ${i < filled ? "bg-brand" : "bg-line"}`} />
            ))}
          </div>
          {others.length > 0 && (
            <p className="mt-2 text-sm text-khaki tnum">
              다른 가능성: {others.map((p) => `${p.name} ${Math.round(p.confidence * 100)}%`).join(", ")}
            </p>
          )}
          {refined && (
            <p className="mt-2 flex items-center gap-1.5 text-sm font-semibold text-brown-deep">
              <span aria-hidden className="icon-[lucide--refresh-cw] h-4 w-4" />
              {uncertain ? "뒷면 사진까지 봤지만 아직 확실하지 않아요" : "뒷면 사진까지 보고 다시 확인했어요"}
            </p>
          )}
          {uncertain && !healthy && !refined && (
            <p className="mt-2 text-sm font-semibold text-signal-med-ink">
              비슷한 병이 여럿 나왔어요. 방제 전에 가까운 농업기술센터에 확인해 보세요.
            </p>
          )}
        </header>

        <div className="mt-5 space-y-5">
          {(result.description || result.causes.length > 0) && <Hairline />}
          {result.description && (
            <section className="space-y-1.5">
              <SectionTitle icon="icon-[lucide--book-open]">증상</SectionTitle>
              <p className="text-base leading-relaxed text-ink">{result.description}</p>
            </section>
          )}
          {result.causes.length > 0 && (
            <section className="space-y-1.5">
              <SectionTitle icon="icon-[lucide--cloud-rain]">왜 생겼을까요</SectionTitle>
              <ul className="space-y-1 text-base leading-relaxed text-ink">
                {result.causes.map((c) => (
                  <li key={c} className="flex gap-2">
                    <span aria-hidden className="mt-[0.7rem] h-1.5 w-1.5 shrink-0 rounded-full bg-khaki" />
                    {c}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {result.pesticides.length > 0 && (
            <>
              <Hairline />
              <section>
                <SectionTitle icon="icon-[lucide--pill]">쓸 수 있는 등록 농약</SectionTitle>
                <ul className="mt-1 divide-y divide-line">
                  {result.pesticides.map((p) => (
                    <li key={p.name} className="py-3.5">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <p className="text-base font-bold text-ink">{p.name}</p>
                          {p.active_ingredient && <p className="text-sm text-khaki">{p.active_ingredient}</p>}
                          {(p.safety.phi_days != null || p.usage) && (
                            <p className="mt-0.5 text-sm text-khaki tnum">
                              {p.safety.phi_days != null && `수확 ${p.safety.phi_days}일 전까지`}
                              {p.safety.phi_days != null && p.usage && ", "}
                              {p.usage}
                            </p>
                          )}
                        </div>
                        {p.dilution && (
                          <div className="shrink-0 text-right">
                            {/* 희석비를 잘못 읽으면 약해로 이어진다 — 이 화면에서 가장 큰 숫자 */}
                            <p className="text-xl font-black text-ink tnum">{p.dilution}</p>
                            <p className="text-xs font-bold text-khaki">희석</p>
                          </div>
                        )}
                      </div>
                      {p.safety_notes && (
                        <p className="mt-2 flex items-start gap-1.5 text-sm font-semibold text-signal-med-ink">
                          <span aria-hidden className="icon-[lucide--triangle-alert] mt-0.5 h-4 w-4 shrink-0" />
                          {p.safety_notes}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            </>
          )}

          {result.prevention.length > 0 && (
            <>
              <Hairline />
              <section className="space-y-1.5">
                <SectionTitle icon="icon-[lucide--shield-check]">{healthy ? "이렇게 관리하세요" : "다시 안 생기게"}</SectionTitle>
                <ul className="space-y-1 text-base leading-relaxed text-ink">
                  {result.prevention.map((p) => (
                    <li key={p} className="flex gap-2">
                      <span aria-hidden className="icon-[lucide--check] mt-1.5 h-4 w-4 shrink-0 text-signal-low-ink" />
                      {p}
                    </li>
                  ))}
                </ul>
              </section>
            </>
          )}
        </div>
      </div>

      {/* 고정 CTA */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 px-5 pb-[max(env(safe-area-inset-bottom),0.75rem)] pt-3 backdrop-blur md:static md:border-0 md:bg-transparent md:px-5 md:pb-6 md:pt-0">
        <div className="mx-auto max-w-app md:max-w-none">
          {onNew ? (
            <button
              type="button"
              onClick={onNew}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-brand py-4 text-base font-bold text-ink shadow-cta transition active:scale-[0.99]"
            >
              <span aria-hidden className="icon-[lucide--camera] h-5 w-5" />
              다른 잎 진단하기
            </button>
          ) : (
            <Link
              href="/"
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-brand py-4 text-base font-bold text-ink shadow-cta transition active:scale-[0.99]"
            >
              <span aria-hidden className="icon-[lucide--camera] h-5 w-5" />
              같은 작물 다시 진단
            </Link>
          )}
          {onNew && (
            <p className="mt-2 flex items-center justify-center gap-1.5 text-sm font-medium text-khaki">
              <span aria-hidden className="icon-[lucide--circle-check] h-4 w-4" />
              이력에 저장했어요
            </p>
          )}
        </div>
      </div>
    </article>
  );
}
