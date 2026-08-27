import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { EvaluateRequest, TaskStatus, GoldenItem, TaskResult, HistoryItem } from '../types';

export function useTaskPolling(taskId: string | null, enabled: boolean) {
  return useQuery<TaskStatus>({
    queryKey: ['task', taskId],
    queryFn: () => api.getTask(taskId!),
    enabled: !!taskId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      if (['COMPLETED', 'FAILED'].includes(data.status)) return false;
      return 2000;
    },
  });
}

export function useGoldens(taskId: string | null) {
  return useQuery<GoldenItem[]>({
    queryKey: ['goldens', taskId],
    queryFn: () => api.getGoldens(taskId!),
    enabled: !!taskId,
  });
}

export function useResults(taskId: string | null) {
  return useQuery<TaskResult>({
    queryKey: ['results', taskId],
    queryFn: () => api.getResults(taskId!),
    enabled: !!taskId,
  });
}

export function useHistory() {
  return useQuery<HistoryItem[]>({
    queryKey: ['history'],
    queryFn: api.getHistory,
  });
}

export function useConfirmGoldens() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => api.confirmGoldens(taskId),
    onSuccess: (_data, taskId) => {
      qc.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });
}

export function useUpdateGolden(taskId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { goldenId: number; data: Partial<Pick<GoldenItem, 'input' | 'expected_output' | 'context'>> }) =>
      api.updateGolden(vars.goldenId, vars.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goldens', taskId] });
    },
  });
}

export function useDeleteGolden(taskId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (goldenId: number) => api.deleteGolden(goldenId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goldens', taskId] });
    },
  });
}

export function useAddGolden(taskId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { input: string; expected_output: string; context?: string | null }) =>
      api.addGolden(taskId!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goldens', taskId] });
    },
  });
}

export function useStartEvaluation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: EvaluateRequest) => api.evaluate(req),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['task', data.task_id] });
    },
  });
}

import { useEffect, useState } from 'react';

import { API_BASE } from '../api/client';

export function useTaskSSE(taskId: string | null) {
  const [progress, setProgress] = useState<{
    phase: string; progress: number; message: string; error?: string;
  } | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    const es = new EventSource(`${API_BASE.replace(/\/api$/, '')}/api/task/${taskId}/stream`);
    es.addEventListener('progress', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setProgress(data);
      setStatus(data.phase || data.status);
    });
    es.addEventListener('complete', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setStatus(data.status);
      es.close();
    });
    es.addEventListener('error', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setProgress((prev) => prev ? { ...prev, error: data.error } : null);
        setStatus('FAILED');
      } catch { /* connection error, EventSource auto-reconnects */ }
    });
    return () => es.close();
  }, [taskId]);

  return { progress, status };
}
