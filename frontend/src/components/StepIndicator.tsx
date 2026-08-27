import { Check } from 'lucide-react';

interface Step {
  n: number;
  label: string;
  hint: string;
}

const STEPS: Step[] = [
  { n: 1, label: '配置与上传', hint: '填入服务地址、模型、上传文档' },
  { n: 2, label: '审核测试样本', hint: '核对 AI 生成的问答对' },
  { n: 3, label: '运行评估', hint: '依次跑分各项指标' },
  { n: 4, label: '查看结果', hint: '通过率与明细' },
];

interface Props {
  current: number; // 1..4
}

export function StepIndicator({ current }: Props) {
  return (
    <div className="flex items-center gap-2 mb-6">
      {STEPS.map((s, i) => {
        const isDone = current > s.n;
        const isCurrent = current === s.n;
        return (
          <div key={s.n} className="flex items-center gap-2 flex-1 last:flex-none">
            <div className="flex items-center gap-2">
              <div
                className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold shrink-0 transition-colors ${
                  isDone
                    ? 'bg-green-500 text-white'
                    : isCurrent
                    ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                    : 'bg-slate-200 text-slate-500'
                }`}
              >
                {isDone ? <Check className="w-4 h-4" /> : s.n}
              </div>
              <div className="hidden sm:block">
                <p className={`text-xs font-semibold ${isCurrent ? 'text-indigo-700' : isDone ? 'text-slate-800' : 'text-slate-400'}`}>
                  {s.label}
                </p>
                <p className="text-[10px] text-slate-400">{isCurrent ? s.hint : ''}</p>
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 rounded ${isDone ? 'bg-green-400' : 'bg-slate-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}