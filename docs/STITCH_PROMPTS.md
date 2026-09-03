# Stitch 프롬프트 — CropCare AI

Stitch에서 1번 프롬프트로 프로젝트를 만든 뒤, 같은 프로젝트 안에서 2~4번을 순서대로 추가하면 스타일이 일관되게 유지됩니다.

---

## 1. 프로젝트 시작 프롬프트 (첫 화면 — 홈/진단)

```
A mobile app called "CropCare AI" for Korean farmers to diagnose crop diseases from photos.

Design style: Clean and minimal like the Korean app Karrot (당근마켓) — flat design, generous whitespace, thin hairline dividers, soft card shadows, rounded corners. Warm and friendly, NOT technical or instrument-like.

Color palette:
- Background: warm paper white #FBF8F1
- Text: brown-black ink #3D2F1A
- Muted text: khaki #8C7B54
- Primary action / highlight: yellow #F5B301 with dark brown text on it
- Deep accent: brown

Typography: Pretendard (Korean sans-serif), extra-bold weights for headings. Single font family only.

Layout: single mobile column, max width 480px, fixed bottom tab bar with 2 tabs: "진단" (Diagnose) and "이력" (History). Active tab in dark ink color, inactive in khaki.

HOME / DIAGNOSE SCREEN:
- Top app bar with app name "CropCare AI"
- Friendly heading like "작물 사진으로 병해충을 진단하세요"
- Crop selector as horizontal chips (고추, 토마토, 감자, 딸기 …) — selected chip filled yellow, others outlined
- Large photo upload area: dashed-border card with camera icon and text "사진을 올려주세요", tap to take photo or choose from gallery
- Big full-width yellow CTA button "진단하기" with dark brown text, rounded
- All UI text in Korean
```

## 2. 진단 결과 화면

```
Add a DIAGNOSIS RESULT screen (same style, same palette, mobile 480px):
- Top: the uploaded crop photo displayed as a rounded card
- Severity band: a horizontal colored strip showing disease severity — green (낮음), amber (보통), or clay/red (높음) with a tint background. This is the ONLY place green/amber/red appear.
- Disease name in Korean as extra-bold heading (e.g. "고추 탄저병") with confidence percentage (e.g. "신뢰도 94%")
- Top-3 predictions list with confidence bars (yellow fill on light track)
- Collapsible or stacked info cards with thin dividers: "병 설명", "발병 원인", "예방 방법"
- Pesticide recommendation section: cards listing registered pesticides with 희석배수 (dilution ratio), 사용법, 안전사용기준
- Bottom: full-width yellow button "이력에 저장됨" state or "다시 진단하기"
- Keep bottom tab bar
```

## 3. 이력 목록 화면

```
Add a HISTORY LIST screen (same style):
- App bar title "진단 이력"
- Vertical list of past diagnoses, each row a flat card: small square crop photo thumbnail on the left, disease name (bold) + crop name + date (khaki muted text) on the right, small severity dot (green/amber/red)
- Thin hairline dividers between items, no heavy borders
- Empty state: friendly illustration placeholder with text "아직 진단 이력이 없어요" and a yellow button "첫 진단 하러 가기"
- Bottom tab bar with "이력" tab active (dark ink)
```

## 4. 이력 상세 화면

```
Add a HISTORY DETAIL screen: identical layout to the diagnosis result screen, but with a back arrow in the app bar, the diagnosis date shown under the disease name, and no "다시 진단하기" button — instead a subtle delete text action at the bottom in khaki.
```

---

## 사용 팁

- 색이 다르게 나오면 후속 프롬프트로 교정: `Use exactly #FBF8F1 background and #F5B301 for all primary buttons`
- 농업 앱이라 Stitch가 초록색을 메인으로 쓰려고 할 수 있음. 그럴 땐: `Do not use green as a primary color, only in the severity indicator`
