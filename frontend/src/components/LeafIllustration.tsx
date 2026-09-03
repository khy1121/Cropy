/**
 * 잎 일러스트 (v2 디자인의 시각 축).
 *
 * - `front`: 앞면. 병반 점 3개. 작물 타일·썸네일·빈 사진 자리에 쓴다.
 * - `back-highlight`: 뒷면 판별 부위를 노란 점선으로 강조. 재촬영 유도 화면 전용.
 *
 * 색은 tailwind의 photo.* 토큰과 같은 값이다(SVG라 currentColor 대신 고정).
 */
interface Props {
  variant?: "front" | "back-highlight";
  className?: string;
}

const OUTLINE =
  "M100 18C58 40 34 84 40 138c3 26 20 40 42 44 44-8 84-44 92-96 4-26-6-52-24-66-16 6-36 4-50-2Z";

export function LeafIllustration({ variant = "front", className = "" }: Props) {
  return (
    <svg
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      className={className}
    >
      <path d={OUTLINE} fill="#8DB36A" />
      <path d={OUTLINE} stroke="#4C7A3F" strokeWidth="4" strokeLinejoin="round" />
      <path d="M82 182C96 146 118 108 160 62" stroke="#4C7A3F" strokeWidth="4" strokeLinecap="round" />
      <path
        d="M96 150c-18-6-30-14-38-26M108 126c-16-4-28-12-36-24M122 104c-12-2-22-8-28-18M138 84c-8 0-14-4-18-10"
        stroke="#4C7A3F"
        strokeWidth="3"
        strokeLinecap="round"
      />
      {variant === "back-highlight" ? (
        <>
          <circle
            cx="112"
            cy="118"
            r="44"
            fill="#F5B301"
            fillOpacity="0.25"
            stroke="#F5B301"
            strokeWidth="4"
            strokeDasharray="10 8"
          />
          <path d="M92 120c8-10 30-10 40 0" stroke="#3D2F1A" strokeWidth="3" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="74" cy="112" r="7" fill="#7A4A2A" />
          <circle cx="118" cy="74" r="9" fill="#7A4A2A" />
          <circle cx="96" cy="140" r="5" fill="#7A4A2A" />
        </>
      )}
    </svg>
  );
}
