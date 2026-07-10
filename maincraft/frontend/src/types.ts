export interface Pack {
  id: string;
  name: string;
}

export interface Chat {
  id: string;
  title: string;
  pack: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatDetail extends Chat {
  messages: Message[];
}

export type StreamEvent =
  | { type: 'token'; content: string }
  | { type: 'tool'; content: string }
  | { type: 'done'; content: string }
  | { type: 'error'; content: string };

export const PACK_COLORS: Record<string, string> = {
  gtnh: 'bg-orange-600',
  e2e: 'bg-blue-600',
  e6: 'bg-purple-600',
  e9: 'bg-green-600',
};

export const PACK_LABELS: Record<string, string> = {
  gtnh: 'GTNH',
  e2e: 'E2E',
  e6: 'E6',
  e9: 'E9',
};

export const STARTER_PROMPTS: Record<string, string[]> = {
  gtnh: [
    "What's next after the Steam Age?",
    "How do I build an Electric Blast Furnace?",
    "What quests should I focus on in LV tier?",
  ],
  e2e: [
    "How do I get started with Tinker's Construct?",
    "What's the progression path to AE2?",
    "How do I make a smeltery?",
  ],
  e6: [
    "What mods should I focus on early game?",
    "How does power generation work in E6?",
    "What's the best ore processing setup?",
  ],
  e9: [
    "What's the early game progression?",
    "How do I set up Create automation?",
    "What are the key quest milestones?",
  ],
};
