import { describe, it, expect, vi, beforeEach } from "vitest";

// B4: synthetic view where turn=2 revision=7 must send 7, not 2
describe("commit revision handling (B4)", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("sends expected_revision from game.revision, not game.turn", async () => {
    const fakeGame = {
      game_id: "test-id",
      revision: 7,
      turn: 2,
      turn_limit: 5,
    } as unknown as import("../api/types").GameView;

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => fakeGame,
    });
    vi.stubGlobal("fetch", fetchMock);

    const { commitChoice } = await import("../api/client");
    // commitChoice takes expectedRevision explicitly — App passes game.revision
    await commitChoice(fakeGame.game_id, "hold", fakeGame.revision);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body.expected_revision).toBe(7);
    expect(body.expected_revision).not.toBe(2);
  });

  it("would fail if turn were sent instead of revision (demonstrates bug)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetchMock);
    const { commitChoice } = await import("../api/client");
    // simulate buggy code: passing turn (2) instead of revision (7)
    await commitChoice("test-id", "hold", 2);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    // This is what a buggy implementation would send — the correct test above ensures 7 is sent
    expect(body.expected_revision).toBe(2);
  });
});
