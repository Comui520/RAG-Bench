import { useState, Fragment } from 'react';
import type { EvalResultItem } from '../types';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { ExpandableText } from './ExpandableText';

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
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="w-full min-w-[760px] table-fixed text-sm">
        <colgroup>
          <col className="w-10" />
          <col className="w-[38%]" />
          <col className="w-[38%]" />
          <col className="w-[14%]" />
        </colgroup>
        <thead>
          <tr className="border-b bg-slate-50">
            <th className="p-3" />
            <th className="p-3 text-left font-semibold text-slate-600">问题</th>
            <th className="p-3 text-left font-semibold text-slate-600">期望答案</th>
            <th className="p-3 text-right font-semibold text-slate-600">结果</th>
          </tr>
        </thead>
        <tbody>
          {details.map((d) => (
            <Fragment key={d.id}>
              <tr
                className="cursor-pointer border-b align-top transition-colors hover:bg-slate-50"
                onClick={() => toggle(d.id)}
              >
                <td className="p-3 align-middle">
                  {expanded.has(d.id) ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
                </td>
                <td className="p-3 align-top">
                  <ExpandableText text={d.input} threshold={90} lines={2} />
                </td>
                <td className="p-3 align-top">
                  <ExpandableText text={d.expected_output} threshold={90} lines={2} />
                </td>
                <td className="p-3 text-right align-middle">
                  <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
                    d.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {d.passed ? '通过' : '未通过'}
                  </span>
                </td>
              </tr>
              {expanded.has(d.id) && (
                <tr>
                  <td colSpan={4} className="border-b bg-slate-50 p-4">
                    <div className="space-y-3">
                      <div>
                        <p className="mb-1 text-xs font-semibold text-slate-500">实际输出</p>
                        <ExpandableText text={d.actual_output} threshold={180} lines={3} />
                      </div>
                      {d.retrieval_context && (
                        <div>
                          <p className="mb-1 text-xs font-semibold text-slate-500">检索依据</p>
                          <ExpandableText text={d.retrieval_context} threshold={180} lines={3} className="rounded-lg bg-white p-3" />
                        </div>
                      )}
                      <div className="flex flex-wrap gap-2">
                        {d.metrics.map((m) => (
                          <span key={m.name} className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600">
                            {m.name}: {(m.score * 100).toFixed(0)}%
                          </span>
                        ))}
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}