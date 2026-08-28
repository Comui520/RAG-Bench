import type { UploadResponse, EvaluateRequest, EvaluateResponse, TaskStatus, GoldenItem, TaskResult, HistoryItem } from '../types';

export const API_BASE = (import.meta.env?.VITE_API_BASE as string | undefined) || 'http://localhost:8000/api';
const DEFAULT_TIMEOUT = 30000;

async function request<T>(path: string, options?: RequestInit & { timeout?: number }): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options?.timeout || DEFAULT_TIMEOUT);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      signal: controller.signal,
      ...options,
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(detail.detail || `HTTP ${res.status}`);
    }
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export async function uploadFiles(files: FileList | File[]): Promise<UploadResponse> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append('files', f));
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
  return res.json();
}

export async function fetchModels(baseUrl: string, apiKey: string): Promise<{ data: { id: string }[] }> {
  const params = new URLSearchParams({ base_url: baseUrl, api_key: apiKey });
  return request(`/models?${params}`);
}

export const api = {
  upload: uploadFiles,
  evaluate: (data: EvaluateRequest) =>
    request<EvaluateResponse>('/evaluate', { method: 'POST', body: JSON.stringify(data) }),
  getTask: (taskId: string) => request<TaskStatus>(`/task/${taskId}`),
  getGoldens: (taskId: string) => request<GoldenItem[]>(`/goldens/${taskId}`),
  updateGolden: (goldenId: number, data: Partial<Pick<GoldenItem, 'input' | 'expected_output' | 'context'>>) =>
    request(`/goldens/${goldenId}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteGolden: (goldenId: number) =>
    request(`/goldens/${goldenId}`, { method: 'DELETE' }),
  addGolden: (taskId: string, data: { input: string; expected_output: string; context?: string | null }) =>
    request<{ id: number }>(`/goldens/${taskId}`, { method: 'POST', body: JSON.stringify(data) }),
  confirmGoldens: (taskId: string) =>
    request<{ status: string }>(`/goldens/${taskId}/confirm`, { method: 'POST' }),
  getResults: (taskId: string) => request<TaskResult>(`/results/${taskId}`),
  getHistory: () => request<HistoryItem[]>('/history'),
  deleteTask: (taskId: string) =>
    request<{ status: string }>(`/tasks/${taskId}`, { method: 'DELETE' }),
  fetchModels,
};
