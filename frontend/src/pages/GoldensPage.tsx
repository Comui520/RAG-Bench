import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useGoldens, useConfirmGoldens, useUpdateGolden, useDeleteGolden, useAddGolden } from '../hooks/useApi';
import { GoldenCard } from '../components/GoldenCard';
import { ConfirmButton } from '../components/ConfirmButton';
import { StepIndicator } from '../components/StepIndicator';
import { Loader2, PlusCircle } from 'lucide-react';
import { toast } from 'sonner';

export function GoldensPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { data: goldens, isLoading } = useGoldens(taskId ?? null);
  const confirm = useConfirmGoldens();
  const update = useUpdateGolden(taskId ?? null);
  const del = useDeleteGolden(taskId ?? null);
  const add = useAddGolden(taskId ?? null);

  const [adding, setAdding] = useState(false);
  const [newInput, setNewInput] = useState('');
  const [newOutput, setNewOutput] = useState('');

  async function handleConfirm() {
    if (!taskId) return;
    try {
      await confirm.mutateAsync(taskId);
      navigate(`/task/${taskId}/progress`);
    } catch {
      toast.error('确认失败，请重试');
    }
  }

  async function handleSave(id: number, data: { input: string; expected_output: string; context?: string | null }) {
    try {
      await update.mutateAsync({ goldenId: id, data });
      toast.success('已保存');
    } catch {
      toast.error('保存失败');
    }
  }

  async function handleDelete(id: number) {
    if (!confirm) return;
    if (!window.confirm('确定删除这条测试样本吗？')) return;
    try {
      await del.mutateAsync(id);
      toast.success('已删除');
    } catch {
      toast.error('删除失败');
    }
  }

  async function handleAdd() {
    if (!taskId) return;
    if (!newInput.trim() || !newOutput.trim()) {
      toast.error('请填写问题和期望答案');
      return;
    }
    try {
      await add.mutateAsync({ input: newInput.trim(), expected_output: newOutput.trim() });
      setNewInput('');
      setNewOutput('');
      setAdding(false);
      toast.success('已添加测试样本');
    } catch {
      toast.error('添加失败');
    }
  }

  if (isLoading) return (
    <div className="flex items-center justify-center py-16 gap-2 text-slate-500">
      <Loader2 className="w-5 h-5 animate-spin" />
      <span>加载测试样本…</span>
    </div>
  );

  return (
    <div>
      <StepIndicator current={2} />
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900">审核测试样本</h2>
        <p className="text-sm text-slate-500 mt-1">
          AI 已根据你的文档生成了 {goldens?.length ?? 0} 条问答对。
          可以编辑、删除或手动添加，确认无误后开始评估。
        </p>
      </div>

      <div className="space-y-3 mb-6">
        {goldens?.map((g, i) => (
          <GoldenCard
            key={g.id}
            index={i}
            input={g.input}
            expectedOutput={g.expected_output}
            context={g.context}
            onSave={(data) => handleSave(g.id, data)}
            onDelete={() => handleDelete(g.id)}
            saving={update.isPending}
          />
        ))}
      </div>

      {/* 手动添加 */}
      {adding ? (
        <div className="border border-dashed border-indigo-300 rounded-xl bg-indigo-50/50 p-4 space-y-3 mb-6">
          <p className="text-sm font-medium text-indigo-800 flex items-center gap-2">
            <PlusCircle className="w-4 h-4" /> 添加一条测试样本
          </p>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">问题</label>
            <input className="w-full border rounded-md px-3 py-2 text-sm" placeholder="输入问题…" value={newInput} onChange={(e) => setNewInput(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">期望答案</label>
            <input className="w-full border rounded-md px-3 py-2 text-sm" placeholder="输入期望答案…" value={newOutput} onChange={(e) => setNewOutput(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} disabled={add.isPending} className="flex items-center gap-1 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
              {add.isPending ? '添加中…' : '添加'}
            </button>
            <button onClick={() => setAdding(false)} className="px-4 py-2 border rounded-lg text-sm hover:bg-white">取消</button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="w-full py-3 border border-dashed border-slate-300 rounded-xl text-sm text-slate-500 hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50/50 transition-colors flex items-center justify-center gap-2 mb-6"
        >
          <PlusCircle className="w-4 h-4" /> 手动添加测试样本
        </button>
      )}

      <ConfirmButton
        onClick={handleConfirm}
        loading={confirm.isPending}
        disabled={!goldens || goldens.length === 0}
        goldensCount={goldens?.length ?? 0}
      />
    </div>
  );
}