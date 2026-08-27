import { useState } from 'react';
import { Loader2, RefreshCw, Eye, EyeOff } from 'lucide-react';

import { API_BASE } from '../api/client';

export interface ModelConfig {
  provider: string;
  model_name: string;
  api_key: string;
  base_url: string;
}

interface Props {
  label: string;
  value: ModelConfig;
  onChange: (config: ModelConfig) => void;
}

const PROVIDERS: Record<string, { base_url: string; models: string[] }> = {
  deepseek: { base_url: 'https://api.deepseek.com', models: ['deepseek-chat', 'deepseek-v4-flash', 'deepseek-v4-pro'] },
  openai: { base_url: 'https://api.openai.com/v1', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1'] },
  anthropic: { base_url: 'https://api.anthropic.com', models: ['claude-sonnet-4-6', 'claude-opus-4-8'] },
  siliconflow: { base_url: 'https://api.siliconflow.cn/v1', models: ['BAAI/bge-m3', 'Pro/BAAI/bge-m3', 'Qwen/Qwen2.5-7B-Instruct'] },
  custom: { base_url: '', models: [] },
};

export function ModelSelector({ label, value, onChange }: Props) {
  const [showKey, setShowKey] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [models, setModels] = useState<string[]>([]);

  function update(fields: Partial<ModelConfig>) {
    onChange({ ...value, ...fields });
  }

  async function fetchModels() {
    if (!value.base_url || !value.api_key) return;
    setFetching(true);
    try {
      const res = await fetch(
        `${API_BASE}/models?base_url=${encodeURIComponent(value.base_url)}&api_key=${encodeURIComponent(value.api_key)}`
      );
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      setModels((data.data || []).map((m: { id: string }) => m.id));
    } catch {
      setModels(PROVIDERS[value.provider]?.models || []);
    } finally {
      setFetching(false);
    }
  }

  function handleProviderChange(provider: string) {
    const preset = PROVIDERS[provider] || PROVIDERS.custom;
    update({ provider, base_url: preset.base_url });
    setModels(preset.models);
  }

  const allModels = models.length > 0 ? models : (PROVIDERS[value.provider]?.models || []);

  return (
    <div className="border rounded-lg bg-white p-4 space-y-3">
      <h4 className="text-sm font-semibold text-slate-700">{label}</h4>
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1">Provider</label>
        <select
          className="w-full border rounded-md px-3 py-2 text-sm"
          value={value.provider}
          onChange={(e) => handleProviderChange(e.target.value)}
        >
          <option value="deepseek">DeepSeek</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="siliconflow">SiliconFlow</option>
          <option value="custom">Custom</option>
        </select>
      </div>
      {value.provider === 'custom' && (
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Base URL</label>
          <input
            className="w-full border rounded-md px-3 py-2 text-sm"
            placeholder="https://api.example.com/v1"
            value={value.base_url}
            onChange={(e) => update({ base_url: e.target.value })}
          />
        </div>
      )}
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1">API Key</label>
        <div className="relative">
          <input
            type={showKey ? 'text' : 'password'}
            className="w-full border rounded-md px-3 py-2 text-sm pr-10"
            placeholder="sk-..."
            value={value.api_key}
            onChange={(e) => update({ api_key: e.target.value })}
          />
          <button type="button" className="absolute right-2 top-2 text-slate-400 hover:text-slate-600" onClick={() => setShowKey(!showKey)}>
            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1">Model</label>
        <div className="flex gap-2">
          {allModels.length > 0 ? (
            <select className="flex-1 border rounded-md px-3 py-2 text-sm" value={value.model_name} onChange={(e) => update({ model_name: e.target.value })}>
              {allModels.map((m) => (<option key={m} value={m}>{m}</option>))}
            </select>
          ) : (
            <input className="flex-1 border rounded-md px-3 py-2 text-sm" placeholder="model-name" value={value.model_name} onChange={(e) => update({ model_name: e.target.value })} />
          )}
          <button type="button" className="px-3 py-2 border rounded-md text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 flex items-center gap-1" onClick={fetchModels} disabled={fetching || !value.base_url || !value.api_key}>
            {fetching ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            Fetch
          </button>
        </div>
      </div>
    </div>
  );
}
