/**
 * 하단 셔터 바(BottomNav)와 진단 폼(DiagnoseForm)을 잇는 얇은 이벤트 브리지.
 *
 * 파일 입력은 사용자 제스처 안에서만 열리므로, 셔터 버튼이 눌린 그 클릭 안에서
 * 폼의 숨은 <input type=file>을 클릭해야 한다. 두 컴포넌트가 트리상 멀리 있어
 * 전역 커스텀 이벤트로 연결한다. 폼이 없는 페이지(이력)에서는 홈으로 이동한다.
 */
export type CaptureMode = "camera" | "album";

const EVENT = "cropcare:capture";

export function requestCapture(mode: CaptureMode) {
  window.dispatchEvent(new CustomEvent<CaptureMode>(EVENT, { detail: mode }));
}

export function onCaptureRequest(handler: (mode: CaptureMode) => void) {
  const listener = (e: Event) => handler((e as CustomEvent<CaptureMode>).detail);
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}
