import { useState, useEffect, type FormEvent } from 'react';
import { ModelSelector, type ModelConfig } from './ModelSelector';
import { saveConfig, loadSavedConfig, clearSavedConfig } from '../utils/storage';
import { History, Trash2 } from 'lucide-react';

export interface FullConfig {
  rag_base_url: string;
  rag_api_key: string;
  rag_model: string;
  eval_model: ModelConfig;
  embed_model: ModelConfig;
}

interface Props {
  onSubmit: (config: FullConfig) => void;
}

const DEFAULT_EVAL: ModelConfig = {
  provider: 'deepseek', api_format: 'openai_chat', model_name: 'deepseek-chat',
  api_key: '', base_url: 'https://api.deepseek.com',
};

const DEFAULT_EMBED: ModelConfig = {
  provider: 'siliconflow', api_format: 'openai_chat', model_name: 'BAAI/bge-m3',
  api_key: '', base_url: 'https://api.siliconflow.cn/v1',
};

export function RagConfigForm({ onSubmit }: Props) {
  const [ragUrl, setRagUrl] = useState('');
  const [ragKey, setRagKey] = useState('');
  const [ragModel, setRagModel] = useState('deepseek-chat');
  const [evalModel, setEvalModel] = useState<ModelConfig>(DEFAULT_EVAL);
  const [embedModel, setEmbedModel] = useState<ModelConfig>(DEFAULT_EMBED);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [hasSaved, setHasSaved] = useState(false);

  // 打开页面时自动回填上次保存的配置
  useEffect(() => {
    const savedConfig = loadSavedConfig();
    if (savedConfig) {
      setRagUrl(savedConfig.rag_base_url || '');
      setRagKey(savedConfig.rag_api_key || '');
      setRagModel(savedConfig.rag_model || 'deepseek-chat');
      setEvalModel(savedConfig.eval_model ?? DEFAULT_EVAL);
      setEmbedModel(savedConfig.embed_model ?? DEFAULT_EMBED);
      setHasSaved(true);
    }
  }, []);

  function handleClear() {
    clearSavedConfig();
    setHasSaved(false);
    setRagUrl('');
    setRagKey('');
    setRagModel('deepseek-chat');
    setEvalModel(DEFAULT_EVAL);
    setEmbedModel(DEFAULT_EMBED);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!ragUrl.trim()) errs.ragUrl = 'RAG 服务地址不能为空';
    if (!ragKey.trim()) errs.ragKey = 'RAG API Key 不能为空';
    if (!evalModel.api_key) errs.evalKey = '评测模型 API Key 不能为空';
    if (!embedModel.api_key) errs.embedKey = '嵌入模型 API Key 不能为空';
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    const config: FullConfig = {
      rag_base_url: ragUrl.trim(), rag_api_key: ragKey.trim(),
      rag_model: ragModel.trim() || 'deepseek-chat',
      eval_model: evalModel, embed_model: embedModel,
    };
    saveConfig(config);
    setHasSaved(true);
    onSubmit(config);
  }

  return (
    <div className="space-y-4">
      {/* 配置记忆条 */}
      {hasSaved && (
        <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
          <span className="text-sm text-blue-800 flex items-center gap-2">
            <History className="w-4 h-4" />
            已自动填入上次的配置
          </span>
          <button type="button" onClick={handleClear}
            className="flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900">
            <Trash2 className="w-3 h-3" /> 清除
          </button>
        </div>
      )}

      {/* RAG Service Card */}
      <div className="border rounded-lg bg-white p-4 space-y-3">
        <h4 className="text-sm font-semibold text-slate-700">被测服务（RAG Service）</h4>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">服务地址 Base URL</label>
          <input className="w-full border rounded-md px-3 py-2 text-sm" placeholder="https://your-rag-service.com/v1" value={ragUrl} onChange={(e) => setRagUrl(e.target.value)} />
          {errors.ragUrl && <p className="text-red-500 text-xs mt-1">{errors.ragUrl}</p>}
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">API Key</label>
          <input type="password" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="sk-..." value={ragKey} onChange={(e) => setRagKey(e.target.value)} />
          {errors.ragKey && <p className="text-red-500 text-xs mt-1">{errors.ragKey}</p>}
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">模型名称</label>
          <input className="w-full border rounded-md px-3 py-2 text-sm" placeholder="deepseek-chat" value={ragModel} onChange={(e) => setRagModel(e.target.value)} />
        </div>
      </div>

      {/* Evaluation Model */}
      <ModelSelector label="评测模型（Evaluation Model）" value={evalModel} onChange={setEvalModel} />
      {errors.evalKey && <p className="text-red-500 text-xs">{errors.evalKey}</p>}

      {/* Embedding Model */}
      <ModelSelector label="嵌入模型（Embedding Model）" value={embedModel} onChange={setEmbedModel} />
      {errors.embedKey && <p className="text-red-500 text-xs">{errors.embedKey}</p>}

      <button type="submit" onClick={handleSubmit}
        className={`w-full py-3 rounded-md text-white font-medium text-sm transition-all active:scale-95 ${
          saved ? 'bg-green-600' : 'bg-slate-900 hover:bg-slate-800'
        }`}>
        {saved ? '✓ 配置已保存' : '保存配置'}
      </button>
    </div>
  );
}