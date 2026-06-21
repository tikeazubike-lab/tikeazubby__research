# Example Atomic Note — Email Deliverability Depends on Reputation

> This is a sample atomic note for the freelance/self-hosting domain.

---

## The Idea

Self-hosted email deliverability is primarily determined by server IP reputation, not just correct SPF/DKIM/DMARC configuration. A new IP starts with zero reputation and must "warm up" gradually.

## Why It Matters

If you're offering self-hosted email as a freelance service, clients will expect their emails to land in the inbox. Understanding reputation mechanics is critical for setting realistic expectations and building reliable systems.

## Details

- **IP Reputation:** Email providers (Gmail, Outlook) track how recipients interact with emails from your IP. High spam complaints = poor reputation.
- **Warm-up protocol:** Start with 10-20 emails/day, double weekly over 4-6 weeks. Never start with high volume.
- **Shared vs Dedicated IP:** Shared IPs inherit others' reputation. Dedicated IPs start clean but require warm-up.
- **Bounce handling:** Hard bounces must be removed immediately. High bounce rate (>5%) destroys reputation.
- **Content matters:** Even with perfect authentication, spammy content triggers filters.
- **Monitoring tools:** Google Postmaster Tools, Microsoft SNDS, MXToolbox.

## Connections

- Related: [[SPF DKIM DMARC configuration]]
- Supports: [[Self-hosted email as a freelance service]]
- Extends: [[Client expectation management for email deliverability]]

## Source

- **Origin:** Personal experience setting up Postfix on Netcup VPS + Google Postmaster documentation
- **First noted:** 2026-06-21

---

## Tags

`#atomic` `#self-hosting` `#email` `#freelance`
