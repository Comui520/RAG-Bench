import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useHistory, useDeleteTask } from '../hooks/useApi';
import { History, Loader2, ArrowRight, Clock3, Server, Tag, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { ExpandableText } from '../components/ExpandableText';
import { toast } from 'sonner';

const PAGE_SIZE = 8;

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
  if (!iso) return '未记录';
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false });
  } catch {
    return '未记录';
  }
}

export function HistoryPage() {
  const navigate = useNavigate();
  const { data: history, isLoading } = useHistory();
  const deleteTask = useDeleteTask();
  const [page, setPage] = useState(1);

  const total = history?.length ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const visibleHistory = useMemo(
    () => (history ?? []).slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [history, page],
  );

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  async function handleDelete(taskId: string, taskName?: string | null) {
    const label = taskName || '这条评估记录';
    if (!window.confirm(`确定删除“${label}”吗？\n相关文档、测试样本和评估结果都会被删除。`)) return;
    try {
      await deleteTask.mutateAsync(taskId);
      toast.success('评估记录已删除');
    } catch {
      toast.error('删除失败，请重试');
    }
  }

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
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">历史记录</h2>
          <p className="text-sm text-slate-500 mt-1">查看和追溯往期的评估任务</p>
        </div>
        <span className="text-xs text-slate-400">共 {total} 条记录</span>
      </div>

      <div className="space-y-3">
        {visibleHistory.map((item) => {
          const canView = ['COMPLETED', 'FAILED'].includes(item.status);
          const canDelete = canView;
          return (
            <article key={item.task_id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-start gap-2">
                    <Tag className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <ExpandableText text={item.task_name || '未命名评估'} threshold={36} lines={2} className="font-semibold text-slate-900" />
                        <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(item.status)}`}>
                          {statusLabel[item.status] ?? item.status}
                        </span>
                      </div>
                      <div className="mt-1 flex items-start gap-1 text-xs text-slate-400">
                        <span className="shrink-0">任务 ID：</span>
                        <ExpandableText text={item.task_id} threshold={18} lines={1} className="font-mono" />
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 border-t border-slate-100 pt-3 sm:grid-cols-2 lg:grid-cols-3">
                    <div className="min-w-0">
                      <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">被测服务</p>
                      <div className="flex items-start gap-1 text-sm text-slate-600">
                        <Server className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                        <ExpandableText text={item.rag_base_url || '—'} threshold={36} lines={2} />
                      </div>
                    </div>
                    <div>
                      <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">创建时间</p>
                      <p className="flex items-start gap-1 text-sm text-slate-600">
                        <Clock3 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                        <span>{formatTime(item.created_at)}</span>
                      </p>
                    </div>
                    <div>
                      <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">完成时间</p>
                      <p className="flex items-start gap-1 text-sm text-slate-600">
                        <Clock3 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                        <span>{formatTime(item.completed_at)}</span>
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2 border-t border-slate-100 pt-3 lg:w-40 lg:flex-col lg:items-stretch lg:border-t-0 lg:border-l lg:pl-4 lg:pt-0">
                  <button
                    onClick={() => navigate(`/task/${item.task_id}/results`)}
                    disabled={!canView}
                    className="inline-flex min-h-9 flex-1 items-center justify-center gap-1 rounded-lg bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-40 lg:flex-none"
                  >
                    查看结果 <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(item.task_id, item.task_name)}
                    disabled={!canDelete || deleteTask.isPending}
                    className="inline-flex min-h-9 items-center justify-center gap-1 rounded-lg px-3 py-2 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> 删除记录
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {pageCount > 1 && (
        <nav className="mt-6 flex flex-wrap items-center justify-center gap-2" aria-label="历史记录分页">
          <button
            type="button"
            aria-label="上一页"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page === 1}
            className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" /> 上一页
          </button>
          {Array.from({ length: pageCount }, (_, index) => index + 1).map((pageNumber) => (
            <button
              key={pageNumber}
              type="button"
              aria-label={`第 ${pageNumber} 页`}
              aria-current={pageNumber === page ? 'page' : undefined}
              onClick={() => setPage(pageNumber)}
              className={`h-9 min-w-9 rounded-lg px-2 text-xs font-medium transition-colors ${
                pageNumber === page
                  ? 'bg-indigo-600 text-white'
                  : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              {pageNumber}
            </button>
          ))}
          <button
            type="button"
            aria-label="下一页"
            onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
            disabled={page === pageCount}
            className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            下一页 <ChevronRight className="h-4 w-4" />
          </button>
        </nav>
      )}
    </div>
  );
}