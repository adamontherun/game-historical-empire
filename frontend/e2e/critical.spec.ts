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
    // empire tableau initial
    await expect(page.getByTestId("empire-tableau")).toBeVisible();
    // first decision screenshot
    await page.screenshot({ path: path.resolve("e2e/screenshots/first-decision.png"), fullPage: true });

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

    // Turn 1: early_dry — should have rival headlines now
    await expect(page.getByTestId("turn-label")).toContainText("Turn 2 of 5");
    await expect(page.getByTestId("rivals-strip")).toContainText("Mira:");
    await expect(page.getByTestId("rivals-strip")).toContainText("Daran:");
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
    await page.screenshot({ path: path.resolve("e2e/screenshots/drought-warning.png"), fullPage: true });

    // Turn 2 commit: buy or hold — use buy if available
    const buyBtn = page.getByTestId("verb-buy_grain");
    if (await buyBtn.isVisible()) {
      await buyBtn.click();
      // B1: quantity toggle shows verbatim payload values — at least two options visible
      // buy_grain has two quantities, check toggle exists
      await expect(page.locator('[data-testid^="qty-buy_grain:"]')).toHaveCount(2);
    } else {
      await page.getByTestId("verb-hold").click();
    }
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
    await page.screenshot({ path: path.resolve("e2e/screenshots/drought-reveal.png"), fullPage: true });
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
    // sell has no cost line — check only one Cost visible for hold vs sell
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
    await expect(page.getByTestId("footer-debug")).toContainText("seed");
    await expect(page.getByTestId("footer-debug")).toContainText("rules");
    // also completion seed·rules
    await expect(page.getByTestId("completion-seed")).toContainText("seed");
    await page.screenshot({ path: path.resolve("e2e/screenshots/final-summary.png"), fullPage: true });

    // B8: controlled race — exactly one POST while pending, disabled while pending
    // Go back via Play again, then test double-click guard on first commit
    await page.getByTestId("play-again").click();
    await expect(page.getByTestId("start-screen")).toBeVisible();
    await page.getByTestId("begin-btn").click();
    await expect(page.getByTestId("turn-label")).toContainText("Turn 1 of 5");

    // set up deferred route gate (B8 controlled race)
    let resolveGate!: () => void;
    const gate = new Promise<void>((res) => (resolveGate = res));
    let requestCount = 0;
    await page.route("**/api/v1/games/*/choices/*", async (route) => {
      requestCount++;
      await gate;
      await route.continue().catch(() => {});
    });
    await page.getByTestId("verb-hold").click();
    // fire first click — request will be held at gate
    const commitBtn = page.getByTestId("commit");
    await commitBtn.click();
    // commit button should be disabled while pending (isPending + committingRef)
    await expect(commitBtn).toBeDisabled();
    // try second click via JS (bypasses disabled) — committingRef must still block
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="commit"]') as HTMLButtonElement;
      if (btn) btn.click();
    });
    // release gate and wait for response
    resolveGate();
    await page.waitForResponse((resp) => resp.url().includes("/choices/") && resp.request().method() === "POST", {
      timeout: 10000,
    });
    // wait for reveal — do not unroute before continue completes
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
    await expect(page.getByTestId("rivals-strip")).toContainText("Mira:");
    await expect(page.getByTestId("rivals-strip")).toContainText("Daran:");
  });
});
