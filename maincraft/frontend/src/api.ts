import type { Chat, ChatDetail, Pack, StreamEvent } from './types';

const BASE = '/api';

export async function fetchPacks(): Promise<Pack[]> {
  const res = await fetch(`${BASE}/packs`);
  return res.json();
}

export async function fetchChats(): Promise<Chat[]> {
  const res = await fetch(`${BASE}/chats`);
  return res.json();
}

export async function createChat(pack = 'gtnh'): Promise<Chat> {
  const res = await fetch(`${BASE}/chats`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pack }),
  });
  return res.json();
}

export async function fetchChat(id: string): Promise<ChatDetail> {
  const res = await fetch(`${BASE}/chats/${id}`);
  return res.json();
}

export async function updateChat(id: string, data: { title?: string; pack?: string }): Promise<Chat> {
  const res = await fetch(`${BASE}/chats/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function deleteChat(id: string): Promise<void> {
  await fetch(`${BASE}/chats/${id}`, { method: 'DELETE' });
}

export async function* streamMessage(chatId: string, content: string): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${BASE}/chats/${chatId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });

  if (!res.ok || !res.body) {
    yield { type: 'error', content: `Request failed: ${res.status}` };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6)) as StreamEvent;
          yield event;
        } catch { /* skip malformed */ }
      }
    }
  }
}

export async function fetchWorld(): Promise<Record<string, string>> {
  const res = await fetch(`${BASE}/world`);
  return res.json();
}

export async function describeWorld(description: string): Promise<string> {
  const res = await fetch(`${BASE}/world/describe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  });
  const data = await res.json();
  return data.result;
}
