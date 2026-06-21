# AI Workflow Guide

> How to use AI effectively and safely in this vault.

---

## The AI Defense Zone

The `60-AI/` folder is a **quarantine zone**. All AI output enters here first.
Nothing from `60-AI/` should be copied directly into permanent notes.

### Rules
1. AI output → `60-AI/Synthesis/` or `60-AI/Connections/`
2. Review and fact-check
3. Rewrite in your own words
4. Move to atomic notes or literature notes
5. Delete or archive the raw AI note

---

## When to Use AI

| Task | Recommended | Model |
|------|-------------|-------|
| Literature synthesis | ✅ Yes | DeepSeek V4 |
| Finding connections | ✅ Yes | DeepSeek V4 |
| Strategy critique | ✅ Yes | DeepSeek V4 |
| Hypothesis generation | ✅ Yes | DeepSeek V4 |
| Code debugging | ✅ Yes | DeepSeek V4 |
| Writing first drafts | ⚠️ With caution | DeepSeek V4 |
| Making trading decisions | ❌ Never | — |
| Writing atomic notes | ❌ Never | — |

---

## Vault Querying Prompts

### "What do I know about X?"
```
Search my vault for all notes related to [TOPIC].
Summarize the key ideas, noting any contradictions or gaps.
Suggest 3 questions I haven't answered yet.
```

### "Connect these ideas"
```
I have these two ideas in my vault:
1. [IDEA A]
2. [IDEA B]

How are they related? What new question emerges from their combination?
What other notes in my vault might connect to both?
```

### "Critique my thinking"
```
Review my recent notes on [TOPIC].
Identify:
1. Logical gaps or unsupported claims
2. Cognitive biases that might be affecting my analysis
3. Alternative perspectives I haven't considered
4. Strongest and weakest arguments
```

---

## Automation Ideas

### Auto-tagging
Use Templater + Dataview to suggest tags based on note content.

### Weekly Review Automation
1. Create a cron job that runs every Sunday
2. It reads the week's new notes
3. Generates a summary using the Weekly Vault Review prompt
4. Saves the synthesis to `60-AI/Weekly-Reviews/`

### Connection Suggestions
Use Smart Connections plugin to auto-suggest related notes when editing.

---

## Model Recommendations

| Use Case | Model | Reason |
|----------|-------|--------|
| Deep analysis | DeepSeek V4 Flash | Best reasoning per dollar |
| Quick tasks | Nex N2 (free) | Fast, free tier available |
| Code | DeepSeek V4 Flash | Strong code understanding |
| Creative | DeepSeek V4 Flash | Good balance of creativity and accuracy |

All models via OpenRouter with your existing API key.
