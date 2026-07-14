import { useParams, useNavigate } from 'react-router-dom';
import { useTaskSSE } from '../hooks/useApi';
import { ProgressTracker } from '../components/ProgressTracker';
import { Loader2, AlertCircle, ArrowLeft, RotateCcw } from 'lucide-react';
import { useEffect } from 'react';

export function ProgressPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { progress, status } = useTaskSSE(taskId ?? null);

  useEffect(() => {
    if (!status) return;
    if (status === 'AWAITING_CONFIRM') {
      navigate(`/task/${taskId}/goldens`);
    } else if (status === 'COMPLETED') {
      const timer = setTimeout(() => navigate(`/task/${taskId}/results`), 2000);
      return () => clearTimeout(timer);
    }
  }, [status, taskId, navigate]);

  if (!progress) {
    return (
      <div className="max-w-xl mx-auto py-12 text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-500" />
        <p className="text-slate-500 mt-4">Connecting to evaluation stream...</p>
      </div>
    );
  }

  if (status === 'FAILED' || progress.error) {
    return (
      <div className="max-w-xl mx-auto space-y-6">
        <h2 className="text-xl font-bold">Evaluation Failed</h2>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-800">Error</p>
            <p className="text-sm text-red-600">{progress.error || 'Unknown error'}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate('/')} className="flex items-center gap-2 px-4 py-2 border rounded-md text-sm hover:bg-slate-50 active:scale-95 transition-transform">
            <ArrowLeft className="w-4 h-4" /> Back to Config
          </button>
          <button onClick={() => window.location.reload()} className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-md text-sm hover:bg-slate-800 active:scale-95 transition-transform">
            <RotateCcw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <h2 className="text-xl font-bold">Evaluation Progress</h2>
      <ProgressTracker phase={progress.phase} progress={progress.progress} status={progress.phase} message={progress.message} />
    </div>
  );
}
