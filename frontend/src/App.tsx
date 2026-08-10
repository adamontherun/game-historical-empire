import { useState, useRef, useEffect } from "react";
import { createGame, commitChoice } from "./api/client";
import type { GameView } from "./api/types";
import { StartScreen } from "./components/StartScreen";
import { HeaderBar } from "./components/HeaderBar";
import { WorldBand } from "./components/WorldBand";
import { EmpireTableau } from "./components/EmpireTableau";
import { MarketPulse } from "./components/MarketPulse";
import { RivalsStrip } from "./components/RivalsStrip";
import { DecisionBlock } from "./components/DecisionBlock";
import { OutcomeReveal } from "./components/OutcomeReveal";
import { CompletionSummary } from "./components/CompletionSummary";
import { FooterDebug } from "./components/FooterDebug";

type Phase = "start" | "decision" | "reveal" | "completion";

export default function App() {
  const [game, setGame] = useState<GameView | null>(null);
  const [phase, setPhase] = useState<Phase>("start");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [committing, setCommitting] = useState(false);
  const committingRef = useRef(false);
  const [toast, setToast] = useState<string | null>(null);

  // B3: phase-selected displayPressure — reveal uses latest_outcome.pressure_stage, else top-level
  const displayPressure =
    phase === "reveal" && game?.latest_outcome ? game.latest_outcome.pressure_stage : (game?.pressure_stage ?? "normal");

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  const handleBegin = async () => {
    try {
      const g = await createGame();
      setGame(g);
      setPhase("decision");
      setSelectedId(null);
    } catch (e) {
      setToast(e instanceof Error ? e.message : String(e));
    }
  };

  const handleCommit = async () => {
    if (!game || !selectedId) return;
    // B8: synchronous ref guard in addition to disabled/isPending
    if (committingRef.current) return;
    committingRef.current = true;
    setCommitting(true);
    try {
      // B4: always game.revision, never game.turn
      const next = await commitChoice(game.game_id, selectedId, game.revision);
      setGame(next);
      // B2: fifth commit has both latest_outcome and completion_summary — show reveal first
      if (next.latest_outcome) {
        setPhase("reveal");
      } else if (next.completion_summary) {
        setPhase("completion");
      }
      setSelectedId(null);
    } catch (e) {
      const err = e as Error & { status?: number };
      // B2/B4/409: check local completion before classifying conflict — never parse detail string
      if (err.status === 409) {
        if (game.completion_summary !== null) {
          setPhase("completion");
        } else {
          // stale — refetch could be done, but for now show toast and stay in decision
          // Try to refetch game to get new revision
          try {
            const { getGame } = await import("./api/client");
            const fresh = await getGame(game.game_id);
            setGame(fresh);
            // if fresh is complete, go to completion
            if (fresh.completion_summary) setPhase("completion");
            else setToast("The game moved on — your view was stale");
          } catch {
            setToast("Conflict — please refresh");
          }
        }
      } else {
        setToast(err.message ?? String(e));
      }
    } finally {
      committingRef.current = false;
      setCommitting(false);
    }
  };

  const handleContinue = () => {
    if (!game) return;
    if (game.completion_summary) {
      setPhase("completion");
    } else {
      setPhase("decision");
    }
  };

  const handleFinish = () => {
    setPhase("completion");
  };

  const handlePlayAgain = () => {
    setGame(null);
    setPhase("start");
    setSelectedId(null);
  };

  if (phase === "start") {
    return (
      <div data-pressure={displayPressure} className="shell">
        <StartScreen onBegin={handleBegin} seed={game?.run_seed} />
        {toast ? (
          <div data-testid="toast" style={{ padding: 12, color: "var(--drought)" }}>
            {toast}
          </div>
        ) : null}
      </div>
    );
  }

  if (!game) {
    return (
      <div data-pressure={displayPressure} className="shell">
        <div style={{ padding: 20 }}>Loading…</div>
      </div>
    );
  }

  if (phase === "completion") {
    return (
      <div data-pressure={displayPressure} className="shell">
        <CompletionSummary game={game} onPlayAgain={handlePlayAgain} />
        {toast ? (
          <div data-testid="toast" style={{ padding: 12, color: "var(--drought)" }}>
            {toast}
          </div>
        ) : null}
      </div>
    );
  }

  if (phase === "reveal") {
    return (
      <div data-pressure={displayPressure} className="shell">
        <HeaderBar turn={game.turn} turnLimit={game.turn_limit} cash={game.player_summary.cash} />
        <WorldBand signal={game.signal} pressureStage={game.pressure_stage} />
        <OutcomeReveal game={game} onContinue={handleContinue} onFinish={handleFinish} />
        <FooterDebug seed={game.run_seed} rules={game.ruleset_version} />
        {toast ? (
          <div data-testid="toast" style={{ padding: 12, color: "var(--drought)" }}>
            {toast}
          </div>
        ) : null}
      </div>
    );
  }

  // decision phase
  return (
    <div data-pressure={displayPressure} className="shell">
      <HeaderBar turn={game.turn} turnLimit={game.turn_limit} cash={game.player_summary.cash} />
      <WorldBand signal={game.signal} pressureStage={game.pressure_stage} />
      <div className="stack">
        <EmpireTableau empire={game.empire_summary} />
        <MarketPulse home={game.home_valley_market} river={game.river_town_market} route={game.route_status} />
        <RivalsStrip headlines={game.rival_headlines} />
        <DecisionBlock
          choices={game.available_choices}
          selectedId={selectedId}
          onSelect={setSelectedId}
          committing={committing}
          onCommit={handleCommit}
        />
      </div>
      <FooterDebug seed={game.run_seed} rules={game.ruleset_version} />
      {toast ? (
        <div data-testid="toast" style={{ padding: 12, color: "var(--drought)" }}>
          {toast}
        </div>
      ) : null}
    </div>
  );
}
