import type { DiagnoseResponse, Severity } from "@/types/diagnosis";

interface Props {
  result: DiagnoseResponse;
}

const SEVERITY: Record<Severity, { label: string; text: string; bg: string; dot: string }> = {
  high: { label: "심각도 높음", text: "text-signal-high-ink", bg: "bg-signal-high-tint", dot: "bg-signal-high" },
  medium: { label: "심각도 보통", text: "text-signal-med-ink", bg: "bg-signal-med-tint", dot: "bg-signal-med" },
  low: { label: "심각도 낮음", text: "text-signal-low-ink", bg: "bg-signal-low-tint", dot: "bg-signal-low" },
};

// 9개 클래스 중 top-1이 이 아래면 후보가 갈렸다고 보고 단정적인 표현을 피한다
const LOW_CONFIDENCE = 0.5;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="mb-2.5 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-khaki">
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-brand" />
      {children}
    </h4>
  );
}

function Shot({ src, alt, label, accent }: { src: string; alt: string; label: string; accent?: boolean }) {
  return (
    <figure className="overflow-hidden rounded-2xl bg-khaki-tint">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} className="h-32 w-full object-cover" />
      <figcaption
        className={`px-2.5 py-1.5 text-xs font-bold ${accent ? "text-brown-deep" : "text-khaki"}`}
      >
        {label}
      </figcaption>
    </figure>
  );
}

export function DiagnosisResult({ result }: Props) {
  const isHealthy = result.category === "normal";
  const severity = SEVERITY[result.severity ?? "medium"];
  const pct = Math.round(result.confidence * 100);
  // 판별부위를 다시 찍어 재확정한 진단은 사진 두 장이 함께 근거가 된다
  const isRefined = Boolean(result.image_url && result.refined_image_url);
  // 확신이 낮을 때까지 "확정했어요"라고 말하면 안 된다 — 문구와 안내를 바꾼다
  const isUncertain = result.confidence < LOW_CONFIDENCE;

  return (
    <div className="space-y-4">
      {/* Diagnosis card */}
      <section className="overflow-hidden rounded-card border border-line bg-surface shadow-card">
        <div className={`flex items-center gap-2 px-5 py-2.5 ${isHealthy ? "bg-signal-low-tint" : severity.bg}`}>
          {isHealthy ? (
            <>
              <span aria-hidden className="icon-[lucide--circle-check] h-4 w-4 text-signal-low-ink" />
              <span className="text-sm font-bold text-signal-low-ink">건강한 상태예요</span>
            </>
          ) : (
            <>
              <span aria-hidden className={`h-2 w-2 rounded-full ${severity.dot}`} />
              <span className={`text-sm font-bold ${severity.text}`}>{severity.label}</span>
            </>
          )}
          {isRefined && (
            <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-surface/80 px-2 py-0.5 text-xs font-bold text-brown-deep">
              <span aria-hidden className="icon-[lucide--scan-search] h-3 w-3" />
              사진 2장 분석
            </span>
          )}
        </div>

        <div className="p-5">
          {isRefined ? (
            <div className="mb-4">
              <div className="grid grid-cols-2 gap-2">
                <Shot src={result.image_url!} alt="처음 촬영한 작물" label="1차 촬영" />
                <Shot
                  src={result.refined_image_url!}
                  alt="판별부위를 다시 촬영한 사진"
                  label="판별부위 재촬영"
                  accent
                />
              </div>
              <p
                className={`mt-2 flex items-start gap-1.5 rounded-xl px-3 py-2 text-xs leading-relaxed ${
                  isUncertain ? "bg-signal-med-tint text-signal-med-ink" : "bg-brand-tint text-brown-deep"
                }`}
              >
                <span
                  aria-hidden
                  className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                    isUncertain ? "icon-[lucide--circle-alert]" : "icon-[lucide--layers]"
                  }`}
                />
                {isUncertain
                  ? "두 장의 결과가 서로 달라 아직 확실하지 않아요. 병징이 뚜렷한 부위를 다시 촬영해 보세요."
                  : "판별부위 사진까지 함께 분석한 결과예요."}
              </p>
            </div>
          ) : (
            result.image_url && (
              <div className="mb-4 overflow-hidden rounded-2xl bg-khaki-tint">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={result.image_url} alt="진단한 작물" className="h-44 w-full object-cover" />
              </div>
            )
          )}

          {result.crop_type && (
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-khaki">{result.crop_type}</p>
          )}
          <h3 className="mt-1 text-2xl font-extrabold leading-tight tracking-tight text-ink">
            {result.disease_name}
          </h3>

          {/* confidence gauge */}
          <div className="mt-4">
            <div className="mb-1.5 flex items-baseline justify-between">
              <span className="text-xs font-semibold text-muted">진단 신뢰도</span>
              <span className="text-2xl font-extrabold tnum text-ink">{pct}%</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-khaki-tint">
              <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${pct}%` }} />
            </div>
            {isUncertain && !isHealthy && (
              <p className="mt-2 flex items-start gap-1.5 text-xs leading-relaxed text-signal-med-ink">
                <span aria-hidden className="icon-[lucide--circle-alert] mt-0.5 h-3.5 w-3.5 shrink-0" />
                비슷한 병해가 여럿 나왔어요. 방제 전에 가까운 농업기술센터에 확인해 보세요.
              </p>
            )}
          </div>

          {result.top_predictions.length > 1 && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-semibold text-muted">그 밖의 가능성</p>
              <div className="flex flex-wrap gap-2">
                {result.top_predictions.slice(1).map((p) => (
                  <span key={p.name} className="rounded-lg bg-paper px-2.5 py-1 text-xs text-muted tnum">
                    {p.name} · {Math.round(p.confidence * 100)}%
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {(result.description || result.causes.length > 0) && (
        <section className="rounded-card border border-line bg-surface p-5 shadow-card">
          {result.description && (
            <>
              <SectionLabel>증상 설명</SectionLabel>
              <p className="text-sm leading-relaxed text-ink/80">{result.description}</p>
            </>
          )}
          {result.description && result.causes.length > 0 && <hr className="my-4 border-line" />}
          {result.causes.length > 0 && (
            <>
              <SectionLabel>발병 원인</SectionLabel>
              <ul className="space-y-2">
                {result.causes.map((c) => (
                  <li key={c} className="flex gap-2.5 text-sm text-ink/80">
                    <span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-khaki" />
                    {c}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}

      {result.pesticides.length > 0 && (
        <section className="rounded-card border border-line bg-surface p-5 shadow-card">
          <SectionLabel>등록 농약 추천</SectionLabel>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            {result.pesticides.map((p) => (
              <div key={p.name} className="rounded-2xl border border-line bg-paper p-4">
                <p className="text-base font-bold text-ink">{p.name}</p>
                {p.active_ingredient && (
                  <p className="mt-0.5 text-xs text-khaki">유효성분 · {p.active_ingredient}</p>
                )}
                {/* 희석비와 안전사용기준은 잘못 읽으면 약해나 잔류농약으로 이어진다.
                    라벨보다 값을 크고 진하게 둬서 잘못 읽을 여지를 줄인다. */}
                <dl className="mt-3 space-y-2 text-sm">
                  {p.dilution && (
                    <div className="flex gap-3">
                      <dt className="w-20 shrink-0 pt-0.5 text-khaki">희석비</dt>
                      <dd className="text-base font-bold text-ink tnum">{p.dilution}</dd>
                    </div>
                  )}
                  {p.usage && (
                    <div className="flex gap-3">
                      <dt className="w-20 shrink-0 text-khaki">사용법</dt>
                      <dd className="text-ink/80">{p.usage}</dd>
                    </div>
                  )}
                  {(p.safety.phi_days != null || p.safety.reentry_hours != null) && (
                    <div className="flex gap-3">
                      <dt className="w-20 shrink-0 pt-0.5 text-khaki">안전기준</dt>
                      <dd className="text-base font-bold text-ink tnum">
                        수확 {p.safety.phi_days ?? "-"}일 전
                        {p.safety.reentry_hours != null && ` · 재입장 ${p.safety.reentry_hours}시간`}
                      </dd>
                    </div>
                  )}
                </dl>
                {p.safety_notes && (
                  <p className="mt-3 flex items-start gap-2 rounded-lg bg-signal-med-tint px-3 py-2.5 text-sm font-semibold text-signal-med-ink">
                    <span aria-hidden className="icon-[lucide--triangle-alert] mt-0.5 h-4 w-4 shrink-0" />
                    {p.safety_notes}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {result.prevention.length > 0 && (
        <section className="rounded-card border border-brand/30 bg-brand-tint p-5">
          <SectionLabel>{isHealthy ? "건강 관리 팁" : "예방 · 재발 방지"}</SectionLabel>
          <ul className="space-y-2.5">
            {result.prevention.map((p) => (
              <li key={p} className="flex gap-2 text-sm text-brown-deep">
                <span aria-hidden className="icon-[lucide--check] mt-0.5 h-4 w-4 shrink-0" />
                {p}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
