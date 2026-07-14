import { useState, type FormEvent } from 'react';
import { ModelSelector, type ModelConfig } from './ModelSelector';

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
  provider: 'deepseek', model_name: 'deepseek-chat',
  api_key: '', base_url: 'https://api.deepseek.com',
};

const DEFAULT_EMBED: ModelConfig = {
  provider: 'siliconflow', model_name: 'BAAI/bge-m3',
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

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!ragUrl.trim()) errs.ragUrl = 'RAG Base URL is required';
    if (!ragKey.trim()) errs.ragKey = 'RAG API Key is required';
    if (!evalModel.api_key) errs.evalKey = 'Evaluation API Key is required';
    if (!embedModel.api_key) errs.embedKey = 'Embedding API Key is required';
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    onSubmit({
      rag_base_url: ragUrl.trim(), rag_api_key: ragKey.trim(),
      rag_model: ragModel.trim() || 'deepseek-chat',
      eval_model: evalModel, embed_model: embedModel,
    });
  }

  return (
    <div className="space-y-4">
      {/* RAG Service Card */}
      <div className="border rounded-lg bg-white p-4 space-y-3">
        <h4 className="text-sm font-semibold text-slate-700">RAG Service (被测服务)</h4>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Base URL</label>
          <input className="w-full border rounded-md px-3 py-2 text-sm" placeholder="https://your-rag-service.com/v1" value={ragUrl} onChange={(e) => setRagUrl(e.target.value)} />
          {errors.ragUrl && <p className="text-red-500 text-xs mt-1">{errors.ragUrl}</p>}
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">API Key</label>
          <input type="password" className="w-full border rounded-md px-3 py-2 text-sm" placeholder="sk-..." value={ragKey} onChange={(e) => setRagKey(e.target.value)} />
          {errors.ragKey && <p className="text-red-500 text-xs mt-1">{errors.ragKey}</p>}
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Model Name</label>
          <input className="w-full border rounded-md px-3 py-2 text-sm" placeholder="deepseek-chat" value={ragModel} onChange={(e) => setRagModel(e.target.value)} />
        </div>
      </div>

      {/* Evaluation Model */}
      <ModelSelector label="Evaluation Model (评测模型)" value={evalModel} onChange={setEvalModel} />
      {errors.evalKey && <p className="text-red-500 text-xs">{errors.evalKey}</p>}

      {/* Embedding Model */}
      <ModelSelector label="Embedding Model (嵌入模型)" value={embedModel} onChange={setEmbedModel} />
      {errors.embedKey && <p className="text-red-500 text-xs">{errors.embedKey}</p>}

      <button type="submit" onClick={handleSubmit}
        className={`w-full py-3 rounded-md text-white font-medium text-sm transition-all active:scale-95 ${
          saved ? 'bg-green-600' : 'bg-slate-900 hover:bg-slate-800'
        }`}>
        {saved ? '✓ Configuration Saved' : 'Save Configuration'}
      </button>
    </div>
  );
}
