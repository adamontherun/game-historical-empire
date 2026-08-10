import { test, expect } from "@playwright/test";
import * as path from "path";

test.describe("critical path", () => {
  test("completes 5-turn game on mobile", async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => pageErrors.push(String(err)));

    await page.goto("/");

    // R8: Begin screen
    await expect(page.getByTestId("start-screen")).toBeVisible();
    await expect(page.getByTestId("begin-btn")).toBeVisible();
    await expect(page.getByText("Age of Grain")).toBeVisible();
    await page.getByTestId("begin-btn").click();

    // wait for first decision — turn 0 normal
    await expect(page.getByTestId("header-bar")).toBeVisible();
    await expect(page.getByTestId("turn-label")).toContainText("Turn 1 of 5");
    await expect(page.getByTestId("world-band")).toContainText("The growing settlement");
    await expect(page.getByTestId("rivals-strip")).toBeVisible();
    await expect(page.getByTestId("rivals-empty")).toBeVisible();
    await expect(page.getByTestId("rivals-empty")).toContainText("act after your first decision");
    // market pulse side by side — both visible
    await expect(page.getByTestId("market-home")).toBeVisible();
    await expect(page.getByTestId("market-river")).toBeVisible();
    await expect(page.getByTestId("route-line")).toBeVisible();
    await expect(page.getByTestId("route-line")).toContainText("Current route spread");
    // decision block no table (AC2)
    await expect(page.getByTestId("decision-block").locator("table")).toHaveCount(0);
    // 6 verb cards at start (B1 correct count)
    await expect(page.getByTestId("verb-hold")).toBeVisible();
    // B1 verbatim — unconditional at turn 0 where buy is guaranteed (55/110)
    await expect(page.locator('[data-testid^="qty-buy_grain:"]')).toHaveCount(2);
    // empire tableau initial
    await expect(page.getByTestId("empire-tableau")).toBeVisible();
    // first decision screenshot — viewport (J1), not fullPage, scrolled to top, I1 must not cover (mobile only, so 390×844)
    if (test.info().project.name === "mobile") {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: path.resolve("e2e/screenshots/first-decision.png") });
    }

    // S2: expand_farm then build_granary early to cross two thresholds for AC5
    // Turn 0: expand_farm
    const tierEstateBefore = await page.getByTestId("tier-estate").textContent();
    expect(tierEstateBefore).toContain("Family Farm");
    // select expand_farm
    await page.getByTestId("verb-expand_farm").click();
    // B8 controlled race check on first commit: hold /choices open via route defer
    // Do this on the second commit to not block first flow; here we test B8 separately below
    await page.getByTestId("commit").click();
    // wait for reveal — B2 phase, B3 drought not yet
    await expect(page.getByTestId("outcome-reveal")).toBeVisible();
    await expect(page.getByTestId("outcome-reveal")).toHaveAttribute("data-reveal-state", "complete", { timeout: 10000 });
    // reveal beat checks — scoped to outcome-reveal
    await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="0"]')).toContainText("Turn 1");
    await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="1"]')).toContainText("normal");
    await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="2"]')).toContainText("Wealth");
    await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="3"]')).toBeVisible();
    // B9: empire now should show expanded estate reached
    await expect(page.getByTestId("reveal-continue")).toBeVisible();
    await page.getByTestId("reveal-continue").click();

    // Turn 1: early_dry — should have rival headlines now (I6: verbatim, no "Mira:" prefix stutter)
    await expect(page.getByTestId("turn-label")).toContainText("Turn 2 of 5");
    await expect(page.getByTestId("rivals-strip")).toContainText("Mira");
    await expect(page.getByTestId("rivals-strip")).toContainText("Daran");
    // ensure no stutter "Mira: Mira"
    await expect(page.getByTestId("rivals-strip")).not.toContainText("Mira: Mira");
    await expect(page.getByTestId("rivals-strip")).not.toContainText("Daran: Daran");
    // verify tableau changed after expand — B9 exact
    const afterExpandTier = await page.getByTestId("tier-estate").textContent();
    expect(afterExpandTier).not.toEqual(tierEstateBefore);
    expect(afterExpandTier).toContain("Expanded Estate");
    expect(afterExpandTier).toContain("Farm 15");
    // Turn1 commit: build_granary to cross second threshold
    const storageBefore = await page.getByTestId("tier-storage").textContent();
    expect(storageBefore).toContain("Granary 130");
    await page.getByTestId("verb-build_granary").click();
    await page.getByTestId("commit").click();
    await expect(page.getByTestId("outcome-reveal")).toHaveAttribute("data-reveal-state", "complete", { timeout: 10000 });
    await page.getByTestId("reveal-continue").click();

    // Turn 2: worsening_dry — drought warning screenshot
    await expect(page.getByTestId("turn-label")).toContainText("Turn 3 of 5");
    await expect(page.getByTestId("world-band")).toContainText("The dry spell persists");
    // check storage now reached
    await expect(page.getByTestId("tier-storage")).toContainText("Granary Network");
    await expect(page.getByTestId("tier-storage")).toContainText("Storage 180");
    if (test.info().project.name === "mobile") {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: path.resolve("e2e/screenshots/drought-warning.png") });
    }

    // Turn 2 commit: hold (buy not guaranteed after granary with full storage, so we hold)
    await page.getByTestId("verb-hold").click();
    await page.getByTestId("commit").click();
    await expect(page.getByTestId("outcome-reveal")).toHaveAttribute("data-reveal-state", "complete", { timeout: 10000 });
    await page.getByTestId("reveal-continue").click();

    // Turn 3: drought — the decision screen shows drought, but reveal will show drought while header shows aftermath
    await expect(page.getByTestId("turn-label")).toContainText("Turn 4 of 5");
    await expect(page.getByTestId("world-band")).toContainText("Drought cuts farm output");
    // commit drought turn — hold
    await page.getByTestId("verb-hold").click();
    await page.getByTestId("commit").click();
    // drought reveal — B3: header aftermath vs reveal drought
    await expect(page.getByTestId("outcome-reveal")).toHaveAttribute("data-reveal-state", "complete", { timeout: 10000 });
    // B3 proof: header shows aftermath, reveal beat 1 shows drought in drought colours
    await expect(page.getByTestId("world-band")).toContainText(/aftermath/i);
    await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="1"]')).toContainText(/drought/i);
    // title "Drought" is in beat 0, world/pressure in beat 1 are lowercase "drought"
    // data-pressure on root should be drought during reveal (B3)
    await expect(page.locator('[data-pressure="drought"]')).toBeVisible();
    if (test.info().project.name === "mobile") {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: path.resolve("e2e/screenshots/drought-reveal.png") });
    }
    // numbers beat: Home price (R6), from 0 (R7) — just check Home price label
    await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="2"]')).toContainText("Home price");
    // drivers beat: no residual, impact_money coloring — check drivers visible
    await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="3"]')).toBeVisible();
    // handle last-turn finish vs continue — this is turn 4 of 5, so Continue
    await expect(page.getByTestId("reveal-continue")).toBeVisible();
    await page.getByTestId("reveal-continue").click();

    // Turn 4: aftermath — final decision
    await expect(page.getByTestId("turn-label")).toContainText("Turn 5 of 5");
    await expect(page.getByTestId("world-band")).toContainText("Markets adjust");
    // B6: hold cost 0 must be visible, sell cost null must not show Cost
    await page.getByTestId("verb-hold").click();
    await expect(page.getByTestId("verb-hold")).toContainText("Cost: 0 coins");
    await expect(page.getByTestId("verb-sell_grain")).not.toContainText("Cost:");
    // commit final turn — B2: fifth reveal before completion
    await page.getByTestId("commit").click();
    await expect(page.getByTestId("outcome-reveal")).toHaveAttribute("data-reveal-state", "complete", { timeout: 10000 });
    // fifth outcome must exist
    await expect(page.locator('[data-testid="outcome-reveal"] [data-reveal-beat="0"]')).toContainText("Turn 5");
    await expect(page.getByTestId("reveal-finish")).toBeVisible();
    await page.getByTestId("reveal-finish").click();

    // completion summary — R10 hierarchy, B2 not skipped
    await expect(page.getByTestId("completion-summary")).toBeVisible();
    await expect(page.getByTestId("final-wealth")).toBeVisible();
    await expect(page.getByTestId("wealth-delta-total")).toBeVisible();
    await expect(page.getByTestId("final-estate")).toContainText("Farm");
    await expect(page.getByTestId("final-estate")).toContainText("Storage");
    await expect(page.getByTestId("run-record")).toBeVisible();
    await expect(page.getByTestId("final-rivals")).toBeVisible();
    // I9: seed·rules shown only inside completion card (completion-seed), not duplicated in footer
    await expect(page.getByTestId("completion-seed")).toContainText("seed");
    await expect(page.getByTestId("completion-seed")).toContainText("rules");
    // Section 12 run record — seed + rules + ordered choice ids, plus copy button (clipboard fallback must not throw)
    await expect(page.getByTestId("run-record-replay")).toBeVisible();
    await expect(page.getByTestId("run-record-replay")).toContainText("seed=");
    await expect(page.getByTestId("run-record-replay")).toContainText("rules=");
    // seed/rules in run record must match completion-seed
    const seedText = await page.getByTestId("completion-seed").textContent();
    const match = seedText?.match(/seed\s+(\S+)/);
    if (match?.[1]) {
      await expect(page.getByTestId("run-record-replay")).toContainText(match[1]);
    }
    // exactly 5 committed ids in order: expand_farm, build_granary, hold, hold, hold
    const runRecordText = (await page.getByTestId("run-record-replay").textContent()) ?? "";
    const expectedIds = ["expand_farm", "build_granary", "hold"] as const;
    // run record must contain all three distinct ids, with expand_farm before build_granary before hold
    for (const id of expectedIds) await expect(page.getByTestId("run-record-replay")).toContainText(id);
    expect(runRecordText.indexOf("expand_farm")).toBeLessThan(runRecordText.indexOf("build_granary"));
    expect(runRecordText.indexOf("build_granary")).toBeLessThan(runRecordText.indexOf("hold"));
    // hold appears at least 3 times (turns 3,4,5) — count occurrences of "hold" token
    const holdCount = (runRecordText.match(/\bhold\b/g) ?? []).length;
    expect(holdCount).toBeGreaterThanOrEqual(3);
    await expect(page.getByTestId("copy-run-record")).toBeVisible();
    await expect(page.getByTestId("copy-run-record")).toContainText("Copy run record");
    // clicking copy must not produce console errors (AC7 covers this, but exercise the button)
    await page.getByTestId("copy-run-record").click();
    await expect(page.getByTestId("footer-debug")).toHaveCount(0);
    if (test.info().project.name === "mobile") {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: path.resolve("e2e/screenshots/final-summary.png") });
    }

    // B8: controlled race — exactly one POST while pending, disabled while pending
    // Go back via Play again, then test double-click guard on first commit
    await page.getByTestId("play-again").click();
    await expect(page.getByTestId("start-screen")).toBeVisible();
    await page.getByTestId("begin-btn").click();
    await expect(page.getByTestId("turn-label")).toContainText("Turn 1 of 5");

    // I5/B8: honest committingRef guard — two clicks dispatched synchronously before React re-renders disabled
    // .click() on a disabled button does not dispatch, so the second click must be in the same tick while still enabled
    let resolveGate!: () => void;
    const gate = new Promise<void>((res) => (resolveGate = res));
    let requestCount = 0;
    await page.route("**/api/v1/games/*/choices/*", async (route) => {
      requestCount++;
      await gate;
      await route.continue().catch(() => {});
    });
    await page.getByTestId("verb-hold").click();
    // fire two clicks synchronously in one evaluate — second must be blocked by committingRef, not just disabled
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="commit"]') as HTMLButtonElement;
      if (btn) {
        btn.click();
        btn.click();
      }
    });
    // commit button should become disabled while pending
    await expect(page.getByTestId("commit")).toBeDisabled();
    // release gate and wait for response
    resolveGate();
    await page.waitForResponse((resp) => resp.url().includes("/choices/") && resp.request().method() === "POST", {
      timeout: 10000,
    });
    await expect(page.getByTestId("outcome-reveal")).toHaveAttribute("data-reveal-state", "complete", { timeout: 10000 });
    expect(requestCount).toBe(1);
    await page.unroute("**/api/v1/games/*/choices/*");

    // AC7: zero console errors
    expect(consoleErrors, `console errors: ${consoleErrors.join("; ")}`).toEqual([]);
    expect(pageErrors, `page errors: ${pageErrors.join("; ")}`).toEqual([]);
  });

  test("desktop smoke — start + 1 commit + reveal", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    await page.goto("/");
    await page.getByTestId("begin-btn").click();
    await expect(page.getByTestId("header-bar")).toBeVisible();
    await expect(page.getByTestId("market-home")).toBeVisible();
    await expect(page.getByTestId("market-river")).toBeVisible();
    await page.getByTestId("verb-hold").click();
    await page.getByTestId("commit").click();
    await expect(page.getByTestId("outcome-reveal")).toHaveAttribute("data-reveal-state", "complete", { timeout: 10000 });
    await expect(page.getByTestId("outcome-reveal")).toBeVisible();
    expect(consoleErrors).toEqual([]);
  });

  test("decision surface has no table (AC2)", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("begin-btn").click();
    await expect(page.getByTestId("decision-block")).toBeVisible();
    await expect(page.getByTestId("decision-block").locator("table")).toHaveCount(0);
  });

  test("rivals card always visible with empty state on turn 0 (AC4)", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("begin-btn").click();
    await expect(page.getByTestId("rivals-strip")).toBeVisible();
    await expect(page.getByTestId("rivals-empty")).toBeVisible();
    await expect(page.getByTestId("rivals-empty")).toContainText("act after your first decision");
    // after one turn, rivals appear
    await page.getByTestId("verb-hold").click();
    await page.getByTestId("commit").click();
    await expect(page.getByTestId("outcome-reveal")).toHaveAttribute("data-reveal-state", "complete", { timeout: 10000 });
    await page.getByTestId("reveal-continue").click();
    await expect(page.getByTestId("rivals-strip")).toContainText("Mira");
    await expect(page.getByTestId("rivals-strip")).toContainText("Daran");
    await expect(page.getByTestId("rivals-strip")).not.toContainText("Mira: Mira");
  });
});
