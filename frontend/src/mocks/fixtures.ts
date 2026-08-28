import type { TaskStatus, GoldenItem, TaskResult, HistoryItem, UploadResponse } from '../types';

export const MOCK_TASK_ID = 'abc123def456abc123def456abc123de';

export const mockUploadResponse: UploadResponse = {
  task_id: MOCK_TASK_ID,
  files: [{ id: 1, filename: 'test.txt', file_size: 1024 }],
};

export const mockTaskStatusGenerating: TaskStatus = {
  task_id: MOCK_TASK_ID,
  status: 'GENERATING_GOLDENS',
  phase: 'GENERATING_GOLDENS',
  progress: 0.5,
  error_message: null,
  created_at: '2026-07-08T00:00:00Z',
  completed_at: null,
};

export const mockTaskStatusAwaiting: TaskStatus = {
  task_id: MOCK_TASK_ID,
  status: 'AWAITING_CONFIRM',
  phase: 'AWAITING_CONFIRM',
  progress: 1.0,
  error_message: null,
  created_at: '2026-07-08T00:00:00Z',
  completed_at: null,
};

export const mockTaskStatusCompleted: TaskStatus = {
  task_id: MOCK_TASK_ID,
  status: 'COMPLETED',
  phase: 'COMPLETED',
  progress: 1.0,
  error_message: null,
  created_at: '2026-07-08T00:00:00Z',
  completed_at: '2026-07-08T00:05:00Z',
};

export const mockGoldens: GoldenItem[] = [
  { id: 1, input: 'What is WidgetX?', expected_output: 'WidgetX is a task management app.', context: '["WidgetX is a revolutionary..."]' },
  { id: 2, input: 'How many pricing tiers?', expected_output: 'Three tiers: Free, Pro, Enterprise.', context: '["WidgetX offers three tiers..."]' },
];

export const mockResults: TaskResult = {
  task_id: MOCK_TASK_ID,
  status: 'COMPLETED',
  overall_scores: [
    { name: 'FaithfulnessMetric', score: 0.92, passed: true },
    { name: 'AnswerRelevancyMetric', score: 0.85, passed: true },
    { name: 'ContextualRelevancyMetric', score: 0.78, passed: true },
  ],
  details: [
    {
      id: 1,
      golden_id: 1,
      input: 'What is WidgetX?',
      expected_output: 'WidgetX is a task management app.',
      actual_output: 'WidgetX is a task management application.',
      retrieval_context: '["WidgetX is a revolutionary..."]',
      metrics: [{ name: 'FaithfulnessMetric', score: 0.92, passed: true }],
      passed: true,
    },
  ],
};

export const mockHistory: HistoryItem[] = [
  {
    task_id: MOCK_TASK_ID,
    task_name: 'WidgetX 回归测试',
    status: 'COMPLETED',
    rag_base_url: 'https://rag.example.com/v1',
    created_at: '2026-07-08T00:00:00Z',
    completed_at: '2026-07-08T00:05:00Z',
  },
];
