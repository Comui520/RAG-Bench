import type { FullConfig } from '../components/RagConfigForm';

const STORAGE_KEY = 'rag-eval:last-config';

/** 保存配置到 localStorage（含 api_key，本地记忆）。 */
export function saveConfig(config: FullConfig): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  } catch {
    // localStorage 不可用（隐私模式等）时静默忽略
  }
}

/** 读取上次保存的配置，无则返回 null；损坏亦返回 null。 */
export function loadSavedConfig(): FullConfig | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // 基本形状校验，避免脏数据回填
    if (
      !parsed ||
      typeof parsed !== 'object' ||
      !parsed.eval_model ||
      !parsed.embed_model
    ) {
      return null;
    }
    return parsed as FullConfig;
  } catch {
    return null;
  }
}

/** 清除已保存的配置。 */
export function clearSavedConfig(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}