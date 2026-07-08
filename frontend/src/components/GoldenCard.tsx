interface Props {
  index: number;
  input: string;
  expectedOutput: string;
  context?: string | null;
}

export function GoldenCard({ index, input, expectedOutput, context }: Props) {
  let parsedContext: string[] = [];
  if (context) {
    try { parsedContext = JSON.parse(context); } catch { parsedContext = [context]; }
  }

  return (
    <div className="border rounded-lg bg-white p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium bg-slate-100 px-2 py-0.5 rounded">#{index + 1}</span>
        <span className="text-sm font-medium text-slate-900">Q: {input}</span>
      </div>
      <div>
        <span className="text-xs font-medium text-slate-500">Expected Answer:</span>
        <p className="text-sm text-slate-700 mt-0.5">{expectedOutput}</p>
      </div>
      {parsedContext.length > 0 && (
        <div>
          <span className="text-xs font-medium text-slate-500">Source Chunks:</span>
          <div className="mt-1 space-y-1">
            {parsedContext.slice(0, 3).map((c, i) => (
              <p key={i} className="text-xs text-slate-500 bg-slate-50 p-1.5 rounded truncate">
                {c}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
