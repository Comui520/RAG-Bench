import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RagConfigForm, type FullConfig } from '../components/RagConfigForm';
import { FileUploader } from '../components/FileUploader';
import { StepIndicator } from '../components/StepIndicator';
import { api } from '../api/client';
import { useStartEvaluation } from '../hooks/useApi';
import type { UploadedFile } from '../types';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

export function ConfigPage() {
  const navigate = useNavigate();
  const [fullConfig, setFullConfig] = useState<FullConfig | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const startEval = useStartEvaluation();

  async function handleUpload(newFiles: File[]) {
    setUploading(true);
    try {
      const resp = await api.upload(newFiles);
      setFiles(resp.files);
      setTaskId(resp.task_id);
    } catch (err) {
      toast.error(`Upload failed: ${err}`);
    } finally {
      setUploading(false);
    }
  }

  async function handleStart() {
    if (!fullConfig || !taskId) return;
    try {
      await startEval.mutateAsync({
        ...fullConfig,
        task_id: taskId,
      });
      navigate(`/task/${taskId}/progress`);
    } catch (err) {
      toast.error(`Failed to start evaluation: ${err}`);
    }
  }

  const canStart = fullConfig && files.length > 0 && taskId;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <StepIndicator current={1} />
      <h2 className="text-2xl font-bold">配置与上传</h2>
      <p className="text-sm text-slate-500 -mt-4">
        配置被测服务与模型，上传知识库文档。配置会自动保存，下次自动填入。
      </p>
      <RagConfigForm onSubmit={setFullConfig} />
      <FileUploader onUpload={handleUpload} files={files} disabled={uploading} />
      <button
        className={`w-full py-3 rounded-md text-white font-medium flex items-center justify-center gap-2 ${
          canStart && !startEval.isPending ? 'bg-slate-900 hover:bg-slate-800' : 'bg-slate-300 cursor-not-allowed'
        }`}
        disabled={!canStart || startEval.isPending}
        onClick={handleStart}
      >
        {startEval.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
        开始评估
      </button>
    </div>
  );
}
