import type { DiagnoseResponse, PaginatedHistory } from "@/types/diagnosis";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function diagnoseImage(file: File, cropType?: string): Promise<DiagnoseResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const params = cropType ? `?crop_type=${encodeURIComponent(cropType)}` : "";

  const res = await fetch(`${API_BASE}/api/v1/diagnose${params}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "진단 요청에 실패했습니다.");
  }

  return res.json();
}

export async function refineDiagnosis(id: string, file: File): Promise<DiagnoseResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/v1/diagnose/${id}/refine`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "재확정 요청에 실패했습니다.");
  }

  return res.json();
}

export async function fetchHistory(page = 1, size = 20): Promise<PaginatedHistory> {
  const res = await fetch(`${API_BASE}/api/v1/history?page=${page}&size=${size}`);
  if (!res.ok) throw new Error("이력 조회에 실패했습니다.");
  return res.json();
}

export async function fetchDiagnosisDetail(id: string): Promise<DiagnoseResponse> {
  const res = await fetch(`${API_BASE}/api/v1/history/${id}`);
  if (!res.ok) throw new Error("진단 상세 조회에 실패했습니다.");
  return res.json();
}
