import { NavLink, Outlet } from 'react-router-dom';
import { useHistory } from '../hooks/useApi';
import { ClipboardList, History, PlusCircle, Clock3 } from 'lucide-react';

export function Layout() {
  const { data: history } = useHistory();

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

  return (
    <div className="flex h-screen bg-slate-50">
      {/* 深色侧边栏 */}
      <aside className="w-64 bg-slate-900 text-slate-200 flex flex-col">
        <div className="p-5 border-b border-slate-800">
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-indigo-400" />
            RAG 评测平台
          </h1>
          <p className="text-[11px] text-slate-500 mt-1">基于 deepeval 的检索增强评估</p>
        </div>

        <nav className="p-3 flex flex-col gap-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-indigo-600 text-white font-medium'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <PlusCircle className="w-4 h-4" />
            新建评估
          </NavLink>
          <NavLink
            to="/history"
            className={({ isActive }) =>
              `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-indigo-600 text-white font-medium'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <History className="w-4 h-4" />
            历史记录
          </NavLink>
        </nav>

        {/* 最近任务 */}
        <div className="flex-1 overflow-auto p-3">
          <div className="flex items-center gap-2 text-[11px] text-slate-500 px-3 mb-2">
            <Clock3 className="w-3 h-3" /> 最近任务
          </div>
          {history?.length ? (
            <div className="space-y-1">
              {history.slice(0, 8).map((item) => (
                <NavLink
                  key={item.task_id}
                  to={`/task/${item.task_id}/results`}
                  className="block px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200 rounded-lg flex items-center justify-between gap-2"
                >
                  <span className="truncate">{item.task_id.slice(0, 8)}…</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${statusColor(item.status)}`}>
                    {statusLabel[item.status] ?? item.status}
                  </span>
                </NavLink>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-600 px-3">暂无任务</p>
          )}
        </div>
      </aside>

      {/* 内容区 */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}