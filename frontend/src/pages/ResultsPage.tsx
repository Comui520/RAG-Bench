import { useParams } from 'react-router-dom';
import { useResults } from '../hooks/useApi';
import { ScoreCard } from '../components/ScoreCard';
import { MetricsRadarChart } from '../components/MetricsRadarChart';
import { DetailTable } from '../components/DetailTable';
import { StepIndicator } from '../components/StepIndicator';
import { Loader2, RefreshCw, FileJson, FileSpreadsheet, CheckCircle2, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import type { TaskResult } from '../types';

function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportCSV(results: TaskResult) {
  const metrics = results.overall_scores.map((s) => s.name);
  const header = ['问题', '期望答案', '实际输出', ...metrics, '是否通过'];
  const rows = results.details.map((d) => {
    const metricVals = metrics.map((m) => {
      const ms = d.metrics.find((x) => x.name === m);
      return ms ? (ms.score * 100).toFixed(1) + '%' : '';
    });
    const esc = (s: string) => `"${(s || '').replace(/"/g, '""')}"`;
    return [esc(d.input), esc(d.expected_output), esc(d.actual_output), ...metricVals, d.passed ? '通过' : '未通过'].join(',');
  });
  download(`results_${results.task_id.slice(0, 8)}.csv`, [header.join(','), ...rows].join('\n'), 'text/csv;charset=utf-8');
}

function exportJSON(results: TaskResult) {
  download(`results_${results.task_id.slice(0, 8)}.json`, JSON.stringify(results, null, 2), 'application/json');
}

export function ResultsPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { data: results, isLoading } = useResults(taskId ?? null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 gap-2 text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>加载结果…</span>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4 text-slate-500">
        <p className="text-lg">结果加载失败</p>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-md hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          重试
        </button>
      </div>
    );
  }

  const passedCount = results.details.filter((d) => d.passed).length;
  const totalCount = results.details.length;
  const passRate = totalCount ? Math.round((passedCount / totalCount) * 100) : 0;
  const r = results;

  function handleExportCSV() {
    try {
      exportCSV(r);
      toast.success('CSV 已导出');
    } catch {
      toast.error('导出失败');
    }
  }

  function handleExportJSON() {
    try {
      exportJSON(r);
      toast.success('JSON 已导出');
    } catch {
      toast.error('导出失败');
    }
  }

  return (
    <div>
      <StepIndicator current={4} />
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">查看结果</h2>
          <p className="text-sm text-slate-500 mt-1">
            共 {totalCount} 条测试样本，通过 {passedCount} 条（{passRate}%）
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExportCSV} className="flex items-center gap-1.5 px-3 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 transition-colors">
            <FileSpreadsheet className="w-4 h-4" /> 导出 CSV
          </button>
          <button onClick={handleExportJSON} className="flex items-center gap-1.5 px-3 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 transition-colors">
            <FileJson className="w-4 h-4" /> 导出 JSON
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {results.overall_scores.map((s) => (
          <ScoreCard key={s.name} name={s.name} score={s.score} />
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="border rounded-xl bg-white p-4 shadow-sm">
          <h3 className="text-base font-semibold mb-2">指标概览</h3>
          <MetricsRadarChart scores={results.overall_scores} />
        </div>
        <div className="border rounded-xl bg-white p-4 shadow-sm">
          <h3 className="text-base font-semibold mb-2">总结</h3>
          <div className="space-y-2 text-sm">
            <p className="flex items-center gap-2">测试样本总数：<strong>{totalCount}</strong></p>
            <p className="flex items-center gap-2 text-green-600">
              <CheckCircle2 className="w-4 h-4" /> 通过：<strong>{passedCount}</strong>
            </p>
            <p className="flex items-center gap-2 text-red-600">
              <XCircle className="w-4 h-4" /> 未通过：<strong>{totalCount - passedCount}</strong>
            </p>
            <div className="pt-2">
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${passRate >= 80 ? 'bg-green-500' : passRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${passRate}%` }} />
              </div>
              <p className="text-xs text-slate-400 mt-1">通过率 {passRate}%</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-base font-semibold mb-3">逐条明细</h3>
        <DetailTable details={results.details} />
      </div>
    </div>
  );
}