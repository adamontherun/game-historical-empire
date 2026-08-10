import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { commitChoice, createGame } from "./client";
import type { GameView } from "./types";

export function useCreateGame() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runSeed?: string) => createGame(runSeed),
    onSuccess: (game) => {
      qc.setQueryData<GameView>(["game", game.game_id], game);
    },
  });
}

export function useGame(gameId: string | null) {
  const { useQuery: _q } = { useQuery };
  void _q;
  return useQuery<GameView>({
    queryKey: ["game", gameId],
    queryFn: async () => {
      const { getGame } = await import("./client");
      return getGame(gameId!);
    },
    enabled: !!gameId,
  });
}

// commit handled in App.tsx with committingRef + isPending per B8
export function useCommit() {
  return useMutation({
    mutationFn: ({
      gameId,
      choiceId,
      expectedRevision,
    }: {
      gameId: string;
      choiceId: string;
      expectedRevision: number;
    }) => commitChoice(gameId, choiceId, expectedRevision),
  });
}
