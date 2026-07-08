import { useState } from 'react';
import type { EvalResultItem } from '../types';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface Props {
  details: EvalResultItem[];
}

export function DetailTable({ details }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  function toggle(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="w-8 p-2" />
            <th className="text-left p-2">Input</th>
            <th className="text-left p-2">Expected Output</th>
            <th className="text-right p-2">Passed</th>
          </tr>
        </thead>
        <tbody>
          {details.map((d) => (
            <>
              <tr key={d.id} className="cursor-pointer hover:bg-slate-50 border-b" onClick={() => toggle(d.id)}>
                <td className="p-2">
                  {expanded.has(d.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </td>
                <td className="p-2 max-w-40 truncate">{d.input}</td>
                <td className="p-2 max-w-40 truncate">{d.expected_output}</td>
                <td className="p-2 text-right">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                    d.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {d.passed ? 'Pass' : 'Fail'}
                  </span>
                </td>
              </tr>
              {expanded.has(d.id) && (
                <tr key={`${d.id}-expanded`}>
                  <td colSpan={4} className="bg-slate-50 p-4">
                    <div className="space-y-2">
                      <p><strong>Actual Output:</strong> {d.actual_output}</p>
                      <div className="flex gap-2 flex-wrap">
                        {d.metrics.map((m) => (
                          <span key={m.name} className="text-xs border rounded px-2 py-0.5">
                            {m.name}: {(m.score * 100).toFixed(0)}%
                          </span>
                        ))}
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}
