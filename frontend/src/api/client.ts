import type { UploadResponse, EvaluateRequest, EvaluateResponse, TaskStatus, GoldenItem, TaskResult, HistoryItem } from '../types';

const API_BASE = 'http://localhost:8000/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function uploadFiles(files: FileList | File[]): Promise<UploadResponse> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append('files', f));
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
  return res.json();
}

export const api = {
  upload: uploadFiles,

  evaluate: (data: EvaluateRequest) =>
    request<EvaluateResponse>('/evaluate', { method: 'POST', body: JSON.stringify(data) }),

  getTask: (taskId: string) =>
    request<TaskStatus>(`/task/${taskId}`),

  getGoldens: (taskId: string) =>
    request<GoldenItem[]>(`/goldens/${taskId}`),

  confirmGoldens: (taskId: string) =>
    request<{ status: string }>(`/goldens/${taskId}/confirm`, { method: 'POST' }),

  getResults: (taskId: string) =>
    request<TaskResult>(`/results/${taskId}`),

  getHistory: () =>
    request<HistoryItem[]>('/history'),
};
