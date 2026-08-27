import { useNavigate } from 'react-router-dom';
import { useHistory } from '../hooks/useApi';
import { History, Loader2, ArrowRight, Clock3, Server } from 'lucide-react';

function statusColor(status: string): string {
  switch (status) {
    case 'COMPLETED': return 'bg-green-100 text-green-700';
    case 'FAILED': return 'bg-red-100 text-red-700';
    case 'RUNNING_EVAL':
    case 'GENERATING_GOLDENS':
    case 'UPLOADING':
    case 'AWAITING_CONFIRM': return 'bg-blue-100 text-blue-700';
    default: return 'bg-slate-100 text-slate-600';
  }
}

const statusLabel: Record<string, string> = {
  COMPLETED: '已完成',
  FAILED: '失败',
  RUNNING_EVAL: '评估中',
  GENERATING_GOLDENS: '生成样本中',
  UPLOADING: '上传中',
  AWAITING_CONFIRM: '待审核',
};

function formatTime(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false });
  } catch {
    return '—';
  }
}

export function HistoryPage() {
  const navigate = useNavigate();
  const { data: history, isLoading } = useHistory();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 gap-2 text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>加载历史记录…</span>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4 text-slate-500">
        <History className="w-12 h-12 text-slate-300" />
        <p className="text-lg font-medium">还没有评估记录</p>
        <p className="text-sm text-slate-400">去创建一个新的评估吧</p>
        <button
          onClick={() => navigate('/')}
          className="mt-2 px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          新建评估
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900">历史记录</h2>
        <p className="text-sm text-slate-500 mt-1">查看和追溯往期的评估任务</p>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-slate-50">
              <th className="text-left p-3 font-semibold text-slate-600">任务 ID</th>
              <th className="text-left p-3 font-semibold text-slate-600">状态</th>
              <th className="text-left p-3 font-semibold text-slate-600">被测服务</th>
              <th className="text-left p-3 font-semibold text-slate-600">创建时间</th>
              <th className="text-left p-3 font-semibold text-slate-600">完成时间</th>
              <th className="text-right p-3 font-semibold text-slate-600">操作</th>
            </tr>
          </thead>
          <tbody>
            {history.map((item) => (
              <tr key={item.task_id} className="border-b last:border-0 hover:bg-slate-50 transition-colors">
                <td className="p-3 font-mono text-slate-700">{item.task_id.slice(0, 12)}…</td>
                <td className="p-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(item.status)}`}>
                    {statusLabel[item.status] ?? item.status}
                  </span>
                </td>
                <td className="p-3 text-slate-600 max-w-40 truncate flex items-center gap-1">
                  <Server className="w-3 h-3 text-slate-400" />
                  {item.rag_base_url || '—'}
                </td>
                <td className="p-3 text-slate-500 flex items-center gap-1">
                  <Clock3 className="w-3 h-3 text-slate-400" />
                  {formatTime(item.created_at)}
                </td>
                <td className="p-3 text-slate-500">{formatTime(item.completed_at)}</td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => navigate(`/task/${item.task_id}/results`)}
                    disabled={!['COMPLETED', 'FAILED'].includes(item.status)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-indigo-600 hover:bg-indigo-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    查看结果 <ArrowRight className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}