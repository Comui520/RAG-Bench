import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RagConfigForm } from '../components/RagConfigForm';
import { FileUploader } from '../components/FileUploader';
import { api } from '../api/client';
import { useStartEvaluation } from '../hooks/useApi';
import type { UploadedFile } from '../types';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

export function ConfigPage() {
  const navigate = useNavigate();
  const [ragConfig, setRagConfig] = useState<{ rag_base_url: string; rag_api_key: string } | null>(null);
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
    if (!ragConfig || !taskId) return;
    try {
      await startEval.mutateAsync({
        rag_base_url: ragConfig.rag_base_url,
        rag_api_key: ragConfig.rag_api_key,
        task_id: taskId,
      });
      navigate(`/task/${taskId}/progress`);
    } catch (err) {
      toast.error(`Failed to start evaluation: ${err}`);
    }
  }

  const canStart = ragConfig && files.length > 0 && taskId;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">RAG Evaluation</h2>
      <RagConfigForm onSubmit={setRagConfig} />
      <FileUploader onUpload={handleUpload} files={files} disabled={uploading} />
      <button
        className={`w-full py-3 rounded-md text-white font-medium flex items-center justify-center gap-2 ${
          canStart && !startEval.isPending ? 'bg-slate-900 hover:bg-slate-800' : 'bg-slate-300 cursor-not-allowed'
        }`}
        disabled={!canStart || startEval.isPending}
        onClick={handleStart}
      >
        {startEval.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
        Start Evaluation
      </button>
    </div>
  );
}
