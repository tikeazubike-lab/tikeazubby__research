# Plugin Setup Guide

> Step-by-step plugin installation for this vault.

---

## Core Plugins (Install First)

### 1. Templater
- **Why:** Advanced template system with date variables and logic
- **Settings:**
  - Templates folder: `70-Resources/Templates`
  - Trigger: `Ctrl+T` for new note from template
  - Enable "Folder Templates" for auto-template on folder creation

### 2. Dataview
- **Why:** Query your vault like a database
- **Settings:**
  - Enable JavaScript queries
  - Set refresh interval to "on file change"
- **Example queries:**
  ```dataview
  LIST FROM #atomic AND #crypto
  SORT file.name ASC
  ```

### 3. Calendar
- **Why:** Navigate daily notes visually
- **Settings:**
  - Daily note format: `YYYY-MM-DD`
  - Daily note folder: `50-Journal/Daily`

### 4. Periodic Notes
- **Why:** Auto-create daily, weekly, monthly notes
- **Settings:**
  - Daily: `50-Journal/Daily/YYYY-MM-DD`
  - Weekly: `50-Journal/Weekly/YYYY-WW`
  - Monthly: `50-Journal/Monthly/YYYY-MM`

---

## Recommended Plugins

### Breadcrumbs
- **Why:** Shows hierarchical navigation between notes
- **Settings:** Set up note-type hierarchy: MOC → Atomic → Fleeting

### Excalidraw
- **Why:** Hand-drawn diagrams for visual thinking
- **Settings:** Default folder: `70-Resources/References/`

### Obsidian Canvas
- **Why:** Visual whiteboard (built-in, no install needed)
- **Use:** Create a visual map of your domains on the Dashboard

### Tracker
- **Why:** Track values over time (portfolio, metrics, habits)
- **Settings:** Data folder: `70-Resources/References/`

---

## AI Plugins

### Smart Connections
- **Why:** AI-powered note similarity (uses OpenAI/OpenRouter API)
- **Settings:**
  - API: OpenRouter
  - Model: `openrouter/deepseek/deepseek-v4-flash`
  - Auto-suggest connections on note open

### Obsidian Copilot
- **Why:** ChatGPT-like interface inside Obsidian
- **Settings:**
  - Provider: OpenRouter
  - Default model: your preference
  - Temperature: 0.3 for research, 0.7 for brainstorming

---

## Research Plugins

### Zotero Integration
- **Why:** Import Zotero references directly into notes
- **Prerequisites:** Zotero + Better BibTeX installed
- **Settings:**
  - Import folder: `20-Literature/Papers`
  - Note format: Use [[TEMPLATE-Literature-Note]]

###Citations
- **Why:** Bibliography management within Obsidian
- **Settings:** Connect to Zotero library

---

## Theme Recommendations

- **Primary:** Obsidian default dark (clean, high contrast)
- **Alternative:** Things theme (excellent for long writing sessions)
- **Accessibility:** Ensure WCAG AA contrast ratios for custom CSS
