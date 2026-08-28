export interface ModelConfig {
  provider: string;
  api_format: string;
  model_name: string;
  api_key: string;
  base_url: string;
}

export interface UploadedFile {
  id: number;
  filename: string;
  file_size: number;
}

export interface UploadResponse {
  task_id: string;
  files: UploadedFile[];
}

export interface EvaluateRequest {
  task_name?: string;
  rag_base_url: string;
  rag_api_key: string;
  rag_model: string;
  eval_model: ModelConfig;
  embed_model: ModelConfig;
  task_id: string;
}

export interface EvaluateResponse {
  task_id: string;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  phase: string;
  progress: number;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface GoldenItem {
  id: number;
  input: string;
  expected_output: string;
  context: string | null;
}

export interface MetricScore {
  name: string;
  score: number;
  passed: boolean;
}

export interface EvalResultItem {
  id: number;
  golden_id: number;
  input: string;
  expected_output: string;
  actual_output: string;
  retrieval_context: string | null;
  metrics: MetricScore[];
  passed: boolean;
}

export interface TaskResult {
  task_id: string;
  status: string;
  overall_scores: MetricScore[];
  details: EvalResultItem[];
}

export interface HistoryItem {
  task_id: string;
  task_name?: string | null;
  status: string;
  rag_base_url: string;
  created_at: string | null;
  completed_at: string | null;
}
