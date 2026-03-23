export interface ProfileMeta {
  type: 'prefill-heavy' | 'decode-heavy' | 'balanced';
  source: 'ShareGPT' | 'Fixed File' | 'Team Logs';
  sourceDetail: string;
  isl: string;
  osl: string;
}

export const PROFILE_META: Record<string, ProfileMeta> = {
  'output-short': { type: 'prefill-heavy', source: 'Fixed File', sourceDetail: 'llm-bench legacy text', isl: '1200', osl: '128' },
  'output-long': { type: 'decode-heavy', source: 'Fixed File', sourceDetail: 'llm-bench legacy text', isl: '180', osl: '1024' },
  'chatbot-short': { type: 'balanced', source: 'ShareGPT', sourceDetail: 'Natural conversation distribution', isl: '≤2000', osl: '≤500' },
  'chatbot-multi-turn': { type: 'balanced', source: 'ShareGPT', sourceDetail: 'Longer conversations', isl: '≤4000', osl: '≤1000' },
  'rag-retrieval': { type: 'prefill-heavy', source: 'ShareGPT', sourceDetail: '2-3 retrieved chunks', isl: '≤6000', osl: '≤1000' },
  'rag-heavy': { type: 'prefill-heavy', source: 'ShareGPT', sourceDetail: 'Many chunks + system prompt', isl: '≤8192', osl: '≤2000' },
  'coding-assist': { type: 'balanced', source: 'ShareGPT', sourceDetail: 'Code generation with context', isl: '≤8192', osl: '≤2048' },
  'coding-heavy': { type: 'balanced', source: 'ShareGPT', sourceDetail: 'Large codebase context', isl: '≤8192', osl: '≤2048' },
  'summarization': { type: 'prefill-heavy', source: 'ShareGPT', sourceDetail: 'Document summarization', isl: '≤8192', osl: '≤1000' },
  'agentic-tool-use': { type: 'balanced', source: 'ShareGPT', sourceDetail: 'Agent step with tool calls', isl: '≤4000', osl: '≤1000' },
  'coding-agent': { type: 'prefill-heavy', source: 'Team Logs', sourceDetail: 'Real SWEBench PLLM calls', isl: '~17000', osl: '~800' },
};

// Color for type badges
export const TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  'prefill-heavy': { bg: 'rgba(249,117,131,0.12)', text: '#f97583', border: 'rgba(249,117,131,0.3)' },
  'decode-heavy': { bg: 'rgba(0,188,212,0.12)', text: '#00bcd4', border: 'rgba(0,188,212,0.3)' },
  'balanced': { bg: 'rgba(63,185,80,0.12)', text: '#3fb950', border: 'rgba(63,185,80,0.3)' },
};

// Color for source badges
export const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  'ShareGPT': { bg: 'rgba(168,85,247,0.12)', text: '#a855f7', border: 'rgba(168,85,247,0.3)' },
  'Fixed File': { bg: 'rgba(255,152,0,0.12)', text: '#ff9800', border: 'rgba(255,152,0,0.3)' },
  'Team Logs': { bg: 'rgba(121,192,255,0.12)', text: '#79c0ff', border: 'rgba(121,192,255,0.3)' },
};
