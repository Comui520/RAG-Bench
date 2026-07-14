import { useParams, useNavigate } from 'react-router-dom';
import { useGoldens, useConfirmGoldens } from '../hooks/useApi';
import { GoldenCard } from '../components/GoldenCard';
import { ConfirmButton } from '../components/ConfirmButton';
import { AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export function GoldensPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { data: goldens, isLoading } = useGoldens(taskId ?? null);
  const confirm = useConfirmGoldens();

  async function handleConfirm() {
    if (!taskId) return;
    try {
      await confirm.mutateAsync(taskId);
      navigate(`/task/${taskId}/progress`);
    } catch {
      toast.error('Failed to confirm goldens');
    }
  }

  if (isLoading) return (
    <div className="flex items-center justify-center py-8 gap-2 text-slate-500">
      <Loader2 className="w-5 h-5 animate-spin" />
      <span>Loading goldens...</span>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <AlertCircle className="w-5 h-5 text-blue-600" />
        <div>
          <h2 className="text-xl font-bold">Review Generated Goldens</h2>
          <p className="text-sm text-slate-500">
            {goldens?.length ?? 0} question-answer pairs generated from your documents.
            Review them before running the full evaluation.
          </p>
        </div>
      </div>

      <div className="max-h-[50vh] overflow-auto space-y-3">
        {goldens?.map((g, i) => (
          <GoldenCard key={g.id} index={i} input={g.input} expectedOutput={g.expected_output} context={g.context} />
        ))}
      </div>

      <ConfirmButton
        onClick={handleConfirm}
        loading={confirm.isPending}
        disabled={!goldens || goldens.length === 0}
        goldensCount={goldens?.length ?? 0}
      />
    </div>
  );
}
