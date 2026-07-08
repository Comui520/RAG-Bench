import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTaskPolling } from '../hooks/useApi';
import { ProgressTracker } from '../components/ProgressTracker';

export function ProgressPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { data: status } = useTaskPolling(taskId ?? null, true);

  useEffect(() => {
    if (!status) return;
    if (status.status === 'AWAITING_CONFIRM') {
      navigate(`/task/${taskId}/goldens`);
    } else if (status.status === 'COMPLETED') {
      navigate(`/task/${taskId}/results`);
    }
  }, [status, taskId, navigate]);

  if (!status) return <p className="text-center text-slate-500 py-8">Loading...</p>;

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <h2 className="text-xl font-bold">Evaluation Progress</h2>
      <ProgressTracker phase={status.phase} progress={status.progress} status={status.status} />
      {status.error_message && (
        <p className="text-red-600 text-sm bg-red-50 p-3 rounded">{status.error_message}</p>
      )}
    </div>
  );
}
