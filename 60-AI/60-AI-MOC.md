---
type: moc
status: active
tags: [moc, ai-layer]
---

# 60 — AI Layer MOC

> **AI as co-pilot, not autopilot.** All AI-generated content lives here first.

---

## Purpose

The AI Layer is the "defense zone" between raw AI output and your permanent notes. AI can summarize, connect, critique, and generate — but nothing enters the atomic notes or literature without your review and rewriting.

---

## AI Defense Zone Rules

1. **All raw AI output goes here first** — never directly into permanent notes
2. **Label AI content clearly** — use `🤖 AI-Generated` tag
3. **Review before promoting** — fact-check, reword, add your own insight
4. **Distinguish your voice** — your original thoughts get `#insight/mine`, AI suggestions get `#insight/ai-suggested`
5. **Never publish AI text as-is** — always add your own analysis

---

## Sub-Folders

- `60-AI/Synthesis/` — AI-generated literature synthesis
- `60-AI/Connections/` — AI-suggested note connections
- `60-AI/Critiques/` — AI critique of your strategies/theses
- `60-AI/Prompts/` — reusable system prompts for common tasks
- `60-AI/Weekly-Reviews/` — AI-assisted weekly vault reviews
- `60-AI/Code/` — AI-generated code snippets, scripts, debugging

---

## Recommended AI Setup

**Cloud (primary):** OpenRouter API
- Model for synthesis: `openrouter/deepseek/deepseek-v4-flash`
- Model for quick tasks: `openrouter/nex-agi/nex-n2-pro:free`

**Local (optional):** Ollama
- Model: `llama3.1:8b` or `mistral:7b` for privacy-sensitive queries

---

## System Prompts

→ [[AI-System-Prompts]] — collection of reusable prompts for vault tasks

---

## Weekly AI Review Prompt

```
You are my research assistant. Review my vault for the past week:
1. List all new atomic notes created
2. Suggest connections between new and existing notes I may have missed
3. Identify any contradictions or gaps in my thinking
4. Summarize key themes from my journal entries
5. Suggest one new research question based on recent notes

Focus on: [domain]
```
