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

export function useStartEvaluation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: EvaluateRequest) => api.evaluate(req),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['task', data.task_id] });
    },
  });
}
