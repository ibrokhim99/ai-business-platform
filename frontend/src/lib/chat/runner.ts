import { ALL_MODELS, type ModelDef, type Spark } from './models';

export type RunStatus = 'pending' | 'running' | 'done' | 'error';

export interface ModelResult {
  modelId: string;
  block: ModelDef['block'];
  title: string;
  status: RunStatus;
  isStub?: boolean;
  latencyMs?: number;
  headline?: { label: string; value: string; tone?: 'pos' | 'neg' | 'neutral' };
  spark?: Spark;
  /** Raw prediction payload — kept so synthesis layers can read structured fields. */
  prediction?: Record<string, unknown>;
  error?: string;
}

/** Initial pending state for every registered model — used to seed the report block. */
export function initialResults(): ModelResult[] {
  return ALL_MODELS.map((m) => ({ modelId: m.modelId, block: m.block, title: m.title, status: 'pending' }));
}
