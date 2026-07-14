import { CheckCircle2, Loader2, Circle, XCircle } from 'lucide-react';

const PHASES = [
  { key: 'UPLOADING', label: 'Uploading' },
  { key: 'GENERATING_GOLDENS', label: 'Generating Goldens' },
  { key: 'AWAITING_CONFIRM', label: 'Review Goldens' },
  { key: 'RUNNING_EVAL', label: 'Running Evaluation' },
  { key: 'COMPLETED', label: 'Completed' },
];

interface Props {
  phase: string;
  progress: number;
  status: string;
  message?: string;
}

export function ProgressTracker({ phase, progress, status, message }: Props) {
  const currentIdx = PHASES.findIndex((p) => p.key === phase);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="flex-1 bg-slate-200 rounded-full h-2">
          <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${Math.round(progress * 100)}%` }} />
        </div>
        <span className="text-sm text-slate-500">{Math.round(progress * 100)}%</span>
      </div>

      {message && (
        <p className="text-sm text-slate-600 bg-blue-50 p-3 rounded-md flex items-center gap-2 mt-4">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500 shrink-0" />
          {message}
        </p>
      )}

      <div className="space-y-3">
        {PHASES.map((p, i) => {
          let Icon = Circle;
          let color = 'text-slate-300';
          if (status === 'FAILED' && i === currentIdx) {
            Icon = XCircle;
            color = 'text-red-500';
          } else if (i < currentIdx || status === 'COMPLETED') {
            Icon = CheckCircle2;
            color = 'text-green-500';
          } else if (i === currentIdx) {
            Icon = Loader2;
            color = 'text-blue-500 animate-spin';
          }
          return (
            <div key={p.key} className="flex items-center gap-3">
              <Icon className={`w-5 h-5 ${color}`} />
              <span className={`text-sm ${i <= currentIdx ? 'text-slate-900 font-medium' : 'text-slate-400'}`}>
                {p.label}
              </span>
              {i === currentIdx && <span className="text-xs font-medium bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Current</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
