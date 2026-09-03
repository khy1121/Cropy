const { addDynamicIconSelectors } = require("@iconify/tailwind");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Warm, clean palette — brown / khaki / yellow
        paper: "#FBF8F1", // soft warm background
        surface: "#FFFFFF", // cards
        ink: "#3D2F1A", // primary text (deep warm brown)
        muted: "#7A6C50", // secondary text
        line: "#ECE5D6", // hairline dividers
        khaki: {
          // darkened from #8C7B54 — the old value was 3.4:1 on khaki-tint,
          // unreadable outdoors for the older farmers this is built for
          DEFAULT: "#766747", // captions / muted accents — 5.5:1 on white
          tint: "#EFEAD9", // soft fills, chips
        },
        brown: {
          DEFAULT: "#6F4E2E",
          deep: "#573A1F",
        },
        brand: {
          DEFAULT: "#F5B301", // yellow — primary action / highlight
          deep: "#DE9F00", // pressed (fill only — fails contrast as text)
          ink: "#916800", // brand-colored TEXT/icons — 4.5:1 on brand-tint
          tint: "#FDF3D3", // highlight background
        },
        // Diagnostic severity signals (warm-tuned).
        // Each has a fill colour (dots, borders) and an -ink colour for text and
        // icons. The fills keep the original hue; the -ink values are darkened to
        // clear 4.5:1 on their own tint background.
        signal: {
          low: "#5E8C4F",
          "low-ink": "#4F7542",
          "low-tint": "#E7F0E0",
          med: "#E8A81C",
          "med-ink": "#8D650E",
          "med-tint": "#FBEFCF",
          high: "#C0522E",
          "high-ink": "#A94829",
          "high-tint": "#F6E2D8",
        },
      },
      // 본문 크기를 한 단계씩 올린다. 주 사용자가 고령 농업인이라 Tailwind
      // 기본값(xs 12px / sm 14px)은 밭에서 읽기에 너무 작다.
      // 클래스명은 그대로 두고 스케일만 재정의해 화면 전체가 일관되게 커진다.
      // 한글은 라틴 문자보다 자간이 촘촘해 행간도 함께 넉넉히 잡는다.
      fontSize: {
        xs: ["0.875rem", { lineHeight: "1.375rem" }], // 12 → 14px
        sm: ["1rem", { lineHeight: "1.625rem" }], // 14 → 16px
        base: ["1.125rem", { lineHeight: "1.75rem" }], // 16 → 18px
        lg: ["1.25rem", { lineHeight: "1.875rem" }], // 18 → 20px
      },
      fontFamily: {
        sans: ["Pretendard", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "1.125rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(61,47,26,0.05), 0 6px 20px -14px rgba(61,47,26,0.18)",
        cta: "0 8px 18px -10px rgba(245,179,1,0.7)",
      },
      maxWidth: {
        app: "30rem",
      },
    },
  },
  plugins: [addDynamicIconSelectors()],
};
