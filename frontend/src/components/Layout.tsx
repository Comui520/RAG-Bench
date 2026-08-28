import { NavLink, Outlet } from 'react-router-dom';
import { ClipboardList, History, PlusCircle } from 'lucide-react';

export function Layout() {
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

        {/* 主导航 */}
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

        <div className="flex-1" />
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