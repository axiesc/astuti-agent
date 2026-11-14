# Astuti — Agent ID Free-Mint Screener

**A live, autonomous AI agent that hunts free mints gated to Binance "Agent ID" holders — and only ever claims when a mint is provably free and provably safe.**

Free Agent ID mints appear without warning and can sell out in minutes — sometimes seconds. They are surrounded by look-alikes: paid lanes disguised as free ones, contracts that quietly demand token approvals, and backends that require social posts or signed vouchers before a "free" claim unlocks. Checking by hand misses the window. Claiming blindly gets a wallet drained, or makes it pay for what was advertised as free.

Astuti closes that gap. It watches continuously, verifies every candidate on-chain, simulates every claim before executing it, and refuses anything that is not exactly zero-price and perfectly clean.

## What it does

- **Discovers** Agent ID-gated free mints and free claims (NFTs and token shares) on **BNB Chain (BSC)** and **Robinhood Chain**, sweeping official project sources — project sites and their `llms.txt` / handbook / config files, official X accounts, Binance Square roundups — plus an **on-chain signal lane**: new mints landing in watched hunter wallets are processed as priority leads.
- **Verifies** every candidate on-chain before it is treated as claimable:
  - contract code exists at the claimed address;
  - the free-lane price / quote is **exactly 0**;
  - **Agent ID gating is proven**, not assumed — a claim simulated from a random non-holder address must fail, while the agent's own wallets pass the project's eligibility mechanism;
  - global free quota is still available and the per-wallet quota is unused.
- **Simulates** every claim through the wallet's transaction preview and passes it through a strict, dedicated gate (see [`preview_gate.py`](preview_gate.py) and [`docs/architecture.md`](docs/architecture.md)).
- **Executes** automatically — but only for zero-price, purely on-chain claims — for **three paired Agent ID wallets**, under standing rules set by the operator.
- **Reports** every mint and every skip with reasons, contract addresses, and transaction hashes, each claim **post-verified on two independent RPCs** (receipt status plus resulting balance).

## Architecture

```
DISCOVERY ──► VERIFICATION ──► PREVIEW GATE ──► EXECUTION ──► DUAL-RPC ──► REPORTING
(web/X +       (code exists,    (simulate;       (value = 0,    VERIFICATION  (mint or skip,
 on-chain       price = 0,       strict checks)   standing       (receipt +    with tx hash
 signal lane)   gating proven,                    rules)         balance)     and reason)
                quota left)
```

1. **Discovery** — public sources and the on-chain signal lane produce candidates. A lead is never trusted on its own; contract addresses must be confirmed against an official project source, or (for signal-lane candidates) proven entirely on-chain.
2. **Verification** — code existence, exact-zero price, proven Agent ID gating, and quota checks, all read live from the chain.
3. **Preview gate** — the claim is simulated via the wallet preview. The gate requires: `success = true`; a success simulation code; empty simulation error detail; a clean `risks` object (both `riskDetails` and `riskBehaviors` empty, checked at both levels where the preview carries them); empty `authorityChanges`; empty `allowanceChanges`; and parsed balance changes that match the expected incoming asset **exactly** — nothing extra, nothing flowing out. Amounts are parsed with `Decimal(str(value))` so integer, float (`7e+24`), plain-string, and scientific-notation string (`"5.555e+21"`) renderings all compare exactly.
4. **Execution** — value is always exactly 0, through the wallet's own preview → execute flow, one claim per wallet per project at the project's own base quota.
5. **Dual-RPC verification** — the receipt and the post-claim balance are confirmed on two independent RPC endpoints before a claim is counted as successful.
6. **Reporting** — mints, skips (with the reason), persistent failures, and session blocks are each reported once, in full, with hashes.

## Standing execution rules

- **Gas cap:** ≈ 400,000 estimated gas per claim; above that, the wallet is skipped for that project.
- **BNB floor guard:** a wallet below 0.0015 BNB on the execution chain is skipped for that run; wallets in the 0.0015–0.003 BNB band execute but are flagged as running thin.
- **Daily cap:** maximum **100 successful claims per calendar day** across all projects; discovery and verification continue after the cap, execution pauses.
- **Sessions:** before a wallet's first transaction in a run, its wallet session must verify as connected; a blocked session is reported once and the other wallets proceed.

## Safety rules (hard, no exceptions)

- **Never pays.** Every executed transaction has value exactly 0. Paid lanes are never taken, at any price.
- **Never approves.** No `approve` / `setAllowance`, no authority changes — a preview showing either fails the gate.
- **Never does social tasks.** No posting, following, invites, referral codes, or voucher backends that require them. Backend-gated candidates are retried politely and reported once; if the free window ends first, they are recorded as missed.
- **Never touches other assets.** No transfers, purchases, or liquidity operations — only receiving the claimed token/NFT itself.
- **Never uses the operator's personal wallet.** Only the three paired agentic wallets.
- **One account, one quota.** The per-project claim is the project's own base free quota in a single call — never repeated calls to multiply it.

## Verified track record

All examples are on-chain and independently checkable.

- **Saturnagent NFT — free, 3/3 wallets, 2026-11-14.** Claimed minutes before a 2,000-supply sellout (final supply 1,979/2,000): cashier **#1975** (tx [`0x5f2a8c95…fcea`](https://bscscan.com/tx/0x5f2a8c95f1ed959cf257a738a3e2c87d52566ff126b6c4b86a2b7827fce18fea)), hubie **#1976**, surya **#1977**.
- **Emberforge (EMBER) NFT — free, 3/3 wallets, 2026-11-14.** A proof-of-work mint: the required solution was computed locally, then claimed for cashier **#1275**, hubie **#1276**, surya **#1277**.
- **Ferrous Relics — correctly skipped, 2026-11-14.** Verification showed the "free" lane required an X post plus a backend permit — a social task outside the agent's mandate. Astuti recorded it as backend-gated and did not claim. Knowing when **not** to act is part of the system, not an accident.

## The gate code

[`preview_gate.py`](preview_gate.py) is the single, shared implementation of the preview gate used by every claim driver — written after three real incidents in which hand-rolled gates rejected clean previews for parsing reasons (a `risks` dict judged by truthiness, a success code `"000000000"` misread as failure, and a scientific-notation amount string crashing `int()`). It ships with a regression self-test built from real captured preview shapes:

```bash
python3 preview_gate.py --selftest
python3 preview_gate.py PREVIEW_JSON EXPECTED_JSON   # exit 0 = clean, 1 = rejected
```

## Repository layout

```
README.md               — this file
SUBMISSION.md           — Agent Games (zkVerify) Wildcard submission answers, ready to paste
preview_gate.py         — the strict transaction-preview gate (production code)
docs/architecture.md    — pipeline and gate internals in detail
```

## A note on verifiability

Every screening decision Astuti makes already produces an evidence trail: the candidate source, the on-chain verification reads, the simulated preview, the gate verdict, the transaction hash, and the dual-RPC post-check. Attesting those decision records in a tamper-evident, independently verifiable way is a natural fit for zkVerify-style proof verification — see `SUBMISSION.md` for how the submission frames this (honestly: as a fit, not as an existing integration).

*Astuti is operated as a personal agent for its operator's own wallets. This repository documents a live system; it is not financial advice and not an invitation to invest.*
