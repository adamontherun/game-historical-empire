import type { GameView } from "./types";

const BASE = ((import.meta as unknown as { env: Record<string, string | undefined> }).env.VITE_API_URL as string | undefined) ?? "/api/v1";

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const err = new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ""}`) as Error & {
      status: number;
      body: string;
    };
    err.status = res.status;
    err.body = text;
    throw err;
  }
  return (await res.json()) as T;
}

export function createGame(runSeed?: string): Promise<GameView> {
  return req<GameView>("/games", {
    method: "POST",
    body: JSON.stringify(runSeed ? { run_seed: runSeed } : {}),
  });
}

export function getGame(gameId: string): Promise<GameView> {
  return req<GameView>(`/games/${gameId}`);
}

export function commitChoice(
  gameId: string,
  choiceId: string,
  expectedRevision: number,
): Promise<GameView> {
  return req<GameView>(`/games/${encodeURIComponent(gameId)}/choices/${encodeURIComponent(choiceId)}`, {
    method: "POST",
    body: JSON.stringify({ expected_revision: expectedRevision }),
  });
}
