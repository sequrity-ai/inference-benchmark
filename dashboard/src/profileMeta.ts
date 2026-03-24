export interface ProfileMeta {
  agentType: 'chat' | 'coding' | 'computer-use' | 'customer-support';
  turnStyle: 'single-turn' | 'multi-turn';
  servingStyle: 'disaggregated' | 'not-disaggregated';
  dataSource: string;    // "sharegpt", "swebench", "file", "random", "test"
  isl: string;
  osl: string;
}

export const PROFILE_META: Record<string, ProfileMeta> = {
  'output-short':         { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'Fixed File', isl: '1200',   osl: '128' },
  'output-long':          { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'Fixed File', isl: '180',    osl: '1024' },
  'chatbot-short':        { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤2000',  osl: '≤500' },
  'chatbot-multi-turn':   { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤4000',  osl: '≤1000' },
  'rag-retrieval':        { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤6000',  osl: '≤1000' },
  'rag-heavy':            { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤2000' },
  'coding-assist':        { agentType: 'coding',           turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤2048' },
  'coding-heavy':         { agentType: 'coding',           turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤2048' },
  'summarization':        { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤1000' },
  'agentic-tool-use':     { agentType: 'chat',             turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤4000',  osl: '≤1000' },
  'coding-agent':         { agentType: 'coding',           turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'SWEBench',   isl: '~17000', osl: '~800' },
  'multi-turn-short':     { agentType: 'chat',             turnStyle: 'multi-turn',  servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤8192',  osl: '≤1000' },
  'multi-turn-long':      { agentType: 'chat',             turnStyle: 'multi-turn',  servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤16384', osl: '≤1500' },
  'computer-use-basic':   { agentType: 'computer-use',     turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT',   isl: '≤4000',  osl: '≤500' },
  'customer-support-basic': { agentType: 'customer-support', turnStyle: 'single-turn', servingStyle: 'not-disaggregated', dataSource: 'ShareGPT', isl: '≤3000',  osl: '≤800' },
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
