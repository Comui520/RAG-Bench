import { useParams } from 'react-router-dom';
import { useResults } from '../hooks/useApi';
import { ScoreCard } from '../components/ScoreCard';
import { MetricsRadarChart } from '../components/MetricsRadarChart';
import { DetailTable } from '../components/DetailTable';

export function ResultsPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { data: results, isLoading } = useResults(taskId ?? null);

  if (isLoading || !results) {
    return <p className="text-center text-slate-500 py-8">Loading results...</p>;
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
