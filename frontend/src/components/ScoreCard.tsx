interface Props {
  name: string;
  score: number;
}

function scoreColor(s: number): string {
  if (s >= 0.8) return 'text-green-600';
  if (s >= 0.6) return 'text-yellow-600';
  return 'text-red-600';
}

export function ScoreCard({ name, score }: Props) {
  return (
    <div className="border rounded-lg bg-white p-4 text-center">
      <p className="text-sm text-slate-500 mb-1">{name}</p>
      <p className={`text-3xl font-bold ${scoreColor(score)}`}>
        {(score * 100).toFixed(1)}%
      </p>
    </div>
  );
}
