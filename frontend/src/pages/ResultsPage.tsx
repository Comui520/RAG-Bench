import { useParams } from 'react-router-dom';
import { useResults } from '../hooks/useApi';
import { ScoreCard } from '../components/ScoreCard';
import { MetricsRadarChart } from '../components/MetricsRadarChart';
import { DetailTable } from '../components/DetailTable';
import { Loader2, RefreshCw } from 'lucide-react';

export function ResultsPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { data: results, isLoading } = useResults(taskId ?? null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 gap-2 text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>Loading results...</span>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-4 text-slate-500">
        <p className="text-lg">Failed to load evaluation results.</p>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-md hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">Evaluation Results</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {results.overall_scores.map((s) => (
          <ScoreCard key={s.name} name={s.name} score={s.score} />
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border rounded-lg bg-white p-4">
          <h3 className="text-base font-semibold mb-2">Metrics Overview</h3>
          <MetricsRadarChart scores={results.overall_scores} />
        </div>
        <div className="border rounded-lg bg-white p-4">
          <h3 className="text-base font-semibold mb-2">Summary</h3>
          <div className="space-y-2 text-sm">
            <p>Total Test Cases: <strong>{results.details.length}</strong></p>
            <p>Passed: <strong>{results.details.filter((d) => d.passed).length}</strong></p>
            <p>Failed: <strong>{results.details.filter((d) => !d.passed).length}</strong></p>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-base font-semibold mb-3">Per-Question Breakdown</h3>
        <DetailTable details={results.details} />
      </div>
    </div>
  );
}
