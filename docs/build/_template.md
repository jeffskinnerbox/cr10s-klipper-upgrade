# Phase NN: <Title>

<!-- Copy this file to docs/build/phase-NN-<slug>.md. Keep every section, in this order. -->

## Purpose

What this phase achieves and why. One short paragraph. Name the user story and the plan phase it belongs to.

## Parts and tools

- Parts: every part used, with the quantity.
- Tools: every tool used, such as screwdrivers, multimeter and crimper.

## Risky steps and recovery

List each irreversible or risky step, such as a firmware flash, mains or heater wiring, or a config change that can stop the printer. For each one, say how to undo it or recover.

| Step | Risk | Undo or recover |
| :-- | :-- | :-- |
| <step number> | <what can go wrong> | <how to get back to a safe state> |

## Steps

Number every step. Each step ends with a photo checkpoint.

1. <Action.>
   📷 <What the photo must show.>
2. <Action.>
   📷 <What the photo must show.>

## Pre-power checklist

Include this section if anything is wired. Do not power on until every box is ticked.

- [ ] Power is off and the PSU is unplugged.
- [ ] Polarity checked on every power connection (V+ and V-).
- [ ] No loose strands or bare wire near other terminals.
- [ ] Every connector is seated and matches the wiring table.
- [ ] A second look at the photos from the steps above.

## Exit test

Numbered pass/fail checks. The phase passes only if every check passes.

1. <Check.> Expected: <result>. PASS / FAIL.
2. <Check.> Expected: <result>. PASS / FAIL.

## Record

Add this row to `docs/build/test-log.md` when the exit test is done:

| Date | Phase/Task | Test | Result | Constitution | Notes |
| :-- | :-- | :-- | :-- | :-- | :-- |
| <YYYY-MM-DD> | <Phase NN / task> | <exit test name> | <PASS or FAIL> | <II ✔ VI ✔> | <notes> |
