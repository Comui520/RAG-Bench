import { useState } from 'react';
import { Pencil, Trash2, Check, X, FileText } from 'lucide-react';

interface Props {
  index: number;
  input: string;
  expectedOutput: string;
  context?: string | null;
  onSave?: (data: { input: string; expected_output: string; context?: string | null }) => void;
  onDelete?: () => void;
  saving?: boolean;
}

export function GoldenCard({ index, input, expectedOutput, context, onSave, onDelete, saving }: Props) {
  const [editing, setEditing] = useState(false);
  const [editInput, setEditInput] = useState(input);
  const [editOutput, setEditOutput] = useState(expectedOutput);
  const [editContext, setEditContext] = useState(context ?? '');

  let parsedContext: string[] = [];
  if (context) {
    try { parsedContext = JSON.parse(context); } catch { parsedContext = [context]; }
  }

  function startEdit() {
    setEditInput(input);
    setEditOutput(expectedOutput);
    setEditContext(context ?? '');
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
  }

  function saveEdit() {
    onSave?.({
      input: editInput.trim(),
      expected_output: editOutput.trim(),
      context: editContext.trim() || null,
    });
    setEditing(false);
  }

  if (editing) {
    return (
      <div className="border rounded-xl bg-white p-4 space-y-3 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded">#{index + 1} · 编辑中</span>
          <div className="flex gap-2">
            <button onClick={cancelEdit} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded hover:bg-slate-100">
              <X className="w-3 h-3" /> 取消
            </button>
            <button onClick={saveEdit} disabled={saving} className="flex items-center gap-1 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 px-2.5 py-1 rounded disabled:opacity-50">
              <Check className="w-3 h-3" /> {saving ? '保存中…' : '保存'}
            </button>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">问题</label>
          <textarea rows={2} className="w-full border rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none" value={editInput} onChange={(e) => setEditInput(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">期望答案</label>
          <textarea rows={2} className="w-full border rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none" value={editOutput} onChange={(e) => setEditOutput(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">来源片段（JSON 数组或文本，可选）</label>
          <textarea rows={2} className="w-full border rounded-md px-3 py-2 text-sm font-mono text-xs focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none" value={editContext} onChange={(e) => setEditContext(e.target.value)} placeholder='["chunk 1", "chunk 2"]' />
        </div>
      </div>
    );
  }

  return (
    <div className="border rounded-xl bg-white p-4 space-y-3 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded">#{index + 1}</span>
          <span className="text-sm font-medium text-slate-900">Q: {input}</span>
        </div>
        <div className="flex gap-1 shrink-0">
          {onSave && (
            <button onClick={startEdit} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="编辑">
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button onClick={onDelete} className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="删除">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
      <div>
        <span className="text-xs font-medium text-slate-500">期望答案：</span>
        <p className="text-sm text-slate-700 mt-0.5">{expectedOutput}</p>
      </div>
      {parsedContext.length > 0 && (
        <div>
          <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
            <FileText className="w-3 h-3" /> 来源片段：
          </span>
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