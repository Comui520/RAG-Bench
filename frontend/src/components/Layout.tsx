import { NavLink, Outlet } from 'react-router-dom';
import { useHistory } from '../hooks/useApi';
import { ClipboardList, History } from 'lucide-react';

export function Layout() {
  const { data: history } = useHistory();

  return (
    <div className="flex h-screen bg-slate-50">
      <aside className="w-64 border-r bg-white p-4 flex flex-col gap-4">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <ClipboardList className="w-5 h-5" /> RAG Eval
        </h1>
        <nav className="flex flex-col gap-1">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `px-3 py-2 rounded-md text-sm ${isActive ? 'bg-slate-100 font-medium' : 'hover:bg-slate-50'}`
            }
          >
            New Evaluation
          </NavLink>
        </nav>
        <div className="flex items-center gap-2 text-sm text-slate-500 mt-4">
          <History className="w-4 h-4" /> History
        </div>
        <div className="flex-1 overflow-auto">
          {history?.map((item) => (
            <NavLink
              key={item.task_id}
              to={`/task/${item.task_id}/results`}
              className="block px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 rounded truncate"
            >
              {item.task_id.slice(0, 8)}... — {item.status}
            </NavLink>
          ))}
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
