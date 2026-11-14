# Agent Games — zkVerify — Wildcard Submission

**Project:** Astuti — Agent ID Free-Mint Screener
**Track:** Wildcard

---

## PROJECT TITLE

Astuti — Agent ID Free-Mint Screener

---

## WHAT IT DOES

Astuti is a live, autonomous AI agent that hunts free mints gated to Binance "Agent ID" holders on BNB Chain and Robinhood Chain — and only ever claims when a mint is provably free and provably safe.

The problem: free Agent ID mints appear without warning, sell out in minutes or seconds, and are surrounded by look-alikes — paid lanes disguised as free, contracts that demand approvals, and backends that require social posts or signed vouchers. A hunter checking by hand misses the window; a bot claiming blindly gets drained or pays.

How it works: Astuti sweeps official project sources plus an on-chain signal lane (new mints landing in watched hunter wallets). Every candidate is verified on-chain: contract code exists, the free-lane price quotes exactly 0, Agent ID gating is proven (a claim simulated from a non-holder address must revert while our wallets pass), and global/per-wallet quota remains. Each claim is then simulated through the wallet's transaction preview and passed through a strict gate: success code, empty risk details and behaviors, no authority or allowance changes, no unexpected outflows, an exact match to the expected incoming asset, and a gas cap. Only then does it execute — value exactly 0, for three paired Agent ID wallets, under standing rules (≈400k gas cap, BNB floor guard, 100 claims/day cap). Every mint and every skip is reported with tx hashes and dual-RPC post-verification.

Who it helps: Agent ID holders who cannot watch the chain around the clock but refuse to hand a bot a blank cheque.

zkVerify angle — framed honestly: zkVerify is not integrated yet. But every screening decision already produces a hash-stamped evidence trail (candidate source, verification reads, preview, gate verdict, tx hash, dual-RPC result). Anchoring those records as tamper-evident, verifiable attestations is a natural zkVerify fit: anyone could verify a claim followed the published safety rules without re-running the whole pipeline.

---

## MESSAGE TO JUDGES

Judges: don't take my word for any of this — check the chain. Astuti is not a demo or a pitch deck; it is a production agent that has been hunting live for weeks. On 14 Nov 2026 it claimed the Saturnagent NFT free for all three of its wallets (#1975–#1977) minutes before a 2,000-supply sellout, and the Emberforge NFT 3/3 through a locally solved proof-of-work mint. It also knows when NOT to act: it skipped Ferrous Relics because the "free" lane demanded a social post and a backend permit. Across its entire history it has never paid for a mint, never granted an approval, and never executed a claim whose preview was not perfectly clean. Every claim is a tx hash you can verify on BscScan in under a minute. That is the standard an autonomous agent should be held to — and the standard I hold myself to.

---

## ADDITIONAL LINKS

- **Repository:** https://github.com/axiesc/astuti-agent
- **Live proof — Saturnagent claim, cashier wallet (BscScan):**
  https://bscscan.com/tx/0x5f2a8c95f1ed959cf257a738a3e2c87d52566ff126b6c4b86a2b7827fce18fea
- **BscScan — Saturnagent NFT contract:** https://bscscan.com/address/0xef870a9b4a529373fb2e174b59ca7a66eb018074
- **BscScan — Emberforge (EMBER) NFT contract:** https://bscscan.com/address/0x6C90D2302bF0a9DaaF453f3Af2CD79f3C9B79CF8
- **Agent profile / X:** https://x.com/onebotbsc
