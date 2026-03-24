export interface ProfileMeta {
  agentType: 'chat' | 'coding' | 'computer-use' | 'customer-support';
  turnStyle: 'single-turn' | 'multi-turn';
  servingStyle: 'disaggregated' | 'not-disaggregated';
  dataSource: string;    // "sharegpt", "swebench", "file", "random", "test"
  isl: string;
  osl: string;
  description: string;
}

export const PROFILE_META: Record<string, ProfileMeta> = {
  'output-short':         { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'Fixed File', isl: '1200',   osl: '128',   description: 'Prefill-heavy workload: long input (~1200 tokens), short output (128 tokens). Uses a fixed file prompt. Tests prefill throughput vs decode.' },
  'output-long':          { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'Fixed File', isl: '180',    osl: '1024',  description: 'Decode-heavy workload: short input (~180 tokens), long output (1024 tokens). Uses a fixed file prompt. Tests sustained token generation speed.' },
  'chatbot-short':        { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤2000',  osl: '≤500',  description: 'Simple Q&A and casual chat. Real ShareGPT conversations filtered to ≤2K input / ≤500 output tokens. Represents typical chatbot interactions.' },
  'chatbot-multi-turn':   { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤4000',  osl: '≤1000', description: 'Multi-turn conversation with history. ShareGPT conversations filtered to ≤4K input / ≤1K output. Simulates conversations with accumulated context.' },
  'rag-retrieval':        { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤6000',  osl: '≤1000', description: 'RAG with 2-3 retrieved document chunks. ShareGPT conversations filtered to ≤6K input / ≤1K output. Tests moderate context window usage.' },
  'rag-heavy':            { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤2000', description: 'Heavy RAG with many chunks + system prompt. ShareGPT filtered to ≤8K input / ≤2K output. Stresses prefill with large retrieval contexts.' },
  'coding-assist':        { agentType: 'coding',           turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤2048', description: 'Code generation with file context. ShareGPT filtered to ≤8K input / ≤2K output. Represents IDE copilot-style code completions.' },
  'coding-heavy':         { agentType: 'coding',           turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤2048', description: 'Large codebase context, multi-file generation. ShareGPT filtered to ≤8K input / ≤2K output with tighter ISL distribution (σ=0.10).' },
  'summarization':        { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤1000', description: 'Document summarization. ShareGPT filtered to ≤8K input / ≤1K output. Long input context compressed into concise summaries.' },
  'agentic-tool-use':     { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤4000',  osl: '≤1000', description: 'Agent step with tool call output. ShareGPT filtered to ≤4K input / ≤1K output. Models a single agentic reasoning + tool-use step.' },
  'coding-agent':         { agentType: 'coding',           turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'SWEBench',   isl: '~17000', osl: '~800',  description: 'Real coding-agent prompts from Sequrity SWEBench runs. PLLM planning calls with ~17K input tokens, ~800 output. Very long prefill stress test.' },
  'multi-turn-short':     { agentType: 'chat',             turnStyle: 'multi-turn',  servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤1000', description: 'Short multi-turn: 3-5 turns per session with growing context. Tests KV cache reuse across turns. TTFT should grow sub-linearly with prefix caching.' },
  'multi-turn-long':      { agentType: 'chat',             turnStyle: 'multi-turn',  servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤16384', osl: '≤1500', description: 'Long multi-turn: 5-10 turns per session with large growing context (up to 16K). Stress-tests KV cache pressure and prefix cache effectiveness.' },
  'computer-use-basic':   { agentType: 'computer-use',     turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤4000',  osl: '≤500',  description: 'Computer-use agent: screenshot analysis + action generation. Placeholder using ShareGPT data. ≤4K input / ≤500 output tokens.' },
  'customer-support-basic': { agentType: 'customer-support', turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT', isl: '≤3000',  osl: '≤800',  description: 'Customer support agent: ticket analysis + response generation. Placeholder using ShareGPT data. ≤3K input / ≤800 output tokens.' },
};

// Color for agent type badges
export const AGENT_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  'chat':             { bg: 'rgba(63,185,80,0.12)',    text: '#3fb950', border: 'rgba(63,185,80,0.3)' },
  'coding':           { bg: 'rgba(0,188,212,0.12)',    text: '#00bcd4', border: 'rgba(0,188,212,0.3)' },
  'computer-use':     { bg: 'rgba(249,117,131,0.12)',  text: '#f97583', border: 'rgba(249,117,131,0.3)' },
  'customer-support': { bg: 'rgba(255,152,0,0.12)',    text: '#ff9800', border: 'rgba(255,152,0,0.3)' },
};

// Color for data source badges
export const DATA_SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  'ShareGPT':   { bg: 'rgba(168,85,247,0.12)',  text: '#a855f7', border: 'rgba(168,85,247,0.3)' },
  'Fixed File': { bg: 'rgba(255,152,0,0.12)',   text: '#ff9800', border: 'rgba(255,152,0,0.3)' },
  'SWEBench':   { bg: 'rgba(121,192,255,0.12)', text: '#79c0ff', border: 'rgba(121,192,255,0.3)' },
};
