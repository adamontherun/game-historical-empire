# Section 13 — Plan Review, Round 1

> Claude, orchestrator. The plan is strong: the thesis is named, the mechanic set is minimal,
> and the grill produced **real computed evidence** (n=200) rather than argument. Two
> escalations are resolved below — `docs/ORCHESTRATION.md` §5 gives me game-design authority
> and instructs the loop to run without pausing, so these are decided, not deferred.

---

## 1. What is settled — keep as planned

- One resource (`skilled_labour`), one verb (`craft_goods`), one curve change. Correct scope.
- Legacies deterministic from final agricultural state, computable from existing data.
- `Land Network` deliberately weak, recorded in `DECISIONS 026`. This is the asymmetry that
  makes AC1 legible — do not let a later reader "balance" it.
- Three epilogue turns; trace nodes for the new mechanics; UI reuses Section 11 unchanged.
- **Excellent grill catch:** `cash_low == 0` in **0 of 800** runs, so a `cash_low > 0`
  threshold for Crisis Reputation would have been trivially always-earned. Buffered threshold
  is right.

---

## 2. BLOCKING — the AC1 control arm is testing the wrong thing

The plan's counter-check is *"legacies-zeroed Arm B must not PASS."* That conflates two
different criteria. Whether legacies are load-bearing is **AC3**. AC1 asks only whether the
previously strong strategy loses ground — and it would be perfectly legitimate for the
**demand shift alone** to cause that.

Meanwhile the confound AC1 actually has is unguarded: **Arm B simply has three more turns than
Arm A.** More turns can reorder policies for reasons having nothing to do with the bottleneck
(compounding curves cross, a slow policy catches up). If that is what moves the rank, AC1
passes while the thesis is undelivered.

**Required — add Control C, the isolation arm:**

> **Control C:** run the epilogue's three turns with the **raw-demand shift disabled** (demand
> stays 410), everything else identical — same policies, same seeds, legacies active.
>
> **AC1 is only credible if Control C does NOT pass the AC1 rule.** If the agricultural winner
> loses rank even without the demand shift, the rank change is an artifact of extra turns and
> AC1 must be re-derived.

Keep the legacies-zeroed arm, but **relabel it as the AC3 control** — it answers "do legacies
visibly alter the epilogue", which is what AC3 asks.

Report all four numbers: Arm A, Arm B, Control C (no demand shift), Control L (no legacies).

---

## 3. RULING — Q5 (demand decay): keep the curve, and stop treating it as taste

Ship `410 → 280 → 220 → 180` as proposed. But the escalation frames this as a product-taste
call, and there is an **objective failure mode** nobody named:

> If the epilogue destroys wealth for **every** policy, it reads as punishment, not a regime
> shift. That directly violates `BUILD_SPEC §13`'s "hook, not a second full game", and it kills
> Section 12 go/no-go criterion 9 ("at least some players want to continue"). Nobody asks for a
> sixth turn of a chapter that took their money.

**Required guard, measurable and cheap:**

> **At least one intentional policy's median final wealth must be HIGHER in Arm B than in
> Arm A.** The epilogue must be net-positive for someone. If every policy is poorer for having
> played it, the curve is too steep — regardless of whether AC1 passes.

That converts a taste question into a test. Tune within the stated ±20% until **both** AC1 and
this guard hold. If they cannot both hold, report that — it means the decay is doing the work
that the *craft opportunity* should be doing, and the fix is a stronger finished-goods upside,
not a gentler collapse.

---

## 4. RULING — Q6 (`hire_labour`): ship it, capped at 1/turn, and it consumes the turn

**`hire_labour` ships.** Without it the epilogue has no decision — the player taps "craft max"
three times and executes a script. `BUILD_SPEC §5` requires one *meaningful* major action per
turn, and an epilogue with no branching fails AC4 ("the player can explain why the new
environment favours a different approach") because they never had an alternative to compare.

Constraints that keep the thesis intact:

1. **Maximum +1 labour per turn.** Over three turns a cash-rich land player adds at most 2–3.
   Money buys *some* labour, slowly — which is also truer than a hard wall: skills take time,
   they are not purchasable in bulk.
2. **Hiring consumes the turn.** It is a major action, mutually exclusive with crafting. That
   is the whole decision: *convert now with the labour I have, or spend a turn on capacity I
   will only get to use once or twice.* If hiring were free or simultaneous with crafting it
   would be a no-brainer and not a trade-off at all.
3. This makes **Crisis Reputation** (cheaper hiring) mechanically meaningful rather than a
   number nobody feels.

If a later playtest shows cash→labour arbitrage re-dominating, the lever to pull is the cap or
the price — not deleting the verb.

---

## 5. SHOULD-FIX — Crisis Reputation currently rewards passivity, not crisis

Earning it on `cash_low >= 300` alone means **a player who holds cash and does nothing earns
it**. That is prudence, not a reputation forged in a crisis, and it rewards the least
interesting behaviour in the game.

**Required:** earn it on **exposure plus survival** — held meaningful inventory into the
drought turn **and** never dropped below the cash floor. Concretely: `inventory_at_drought >= X`
**and** `cash_low >= 300`. Pick `X` from measured runs so the legacy lands in the same ~25–40%
band as the others, and report the observed rate.

This keeps the name honest and rewards the anticipatory play the whole game is built around.

---

## 6. SHOULD-FIX — state the labour cap interaction with Land Network explicitly

`Land Network` grants +15 grain/turn while `craft_goods` is capped at `labour × 10`. So for a
low-labour player the extra grain **cannot be converted at all** and can only be dumped into a
declining raw market. That is exactly the intended weakness — but it is currently implicit.

Write it into `DECISIONS 026` in one line, with the arithmetic, so the interaction is a
documented design intent rather than something a later reader "discovers" as a bug and fixes.

---

## 7. Not asked for

Sections 14+, a full craft chain, new rivals, a second pressure arc, any new visual system.
Section 14 is explicitly gated on this hook and the five-turn loop **testing well with humans**
— Section 12 is `BLOCKED — AWAITING HUMAN PLAYTEST`, so 14 stays untouched.

---

## 8. Instruction to Muse

1. Revise the plan for §2 (Control C + relabel the legacies arm to AC3), §3 (net-positive
   guard), §4 (`hire_labour` 1/turn, consumes the turn), §5 (Crisis Reputation exposure), §6.
2. Then implement. Report the **observed** four-arm numbers — Arm A, Arm B, Control C,
   Control L — and the net-positive guard result, whatever they say.
3. If AC1 fails, say so plainly and retune the regime; do not reword the criterion.
4. All gates green (`make check-all` + `npx playwright test`), observed output into `STATE.md`,
   `graphify update .`, commit, push.
