# PDF Bot

Auto-generates and sells PDF guides from trending topics. Runs 100% on GitHub Actions — zero server cost.

## Setup (5 minutes)

### 1. Fork this repo

### 2. Add GitHub Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Where to get it |
|--------|----------------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) — free |
| `GUMROAD_TOKEN` | [app.gumroad.com/settings/advanced](https://app.gumroad.com/settings/advanced) — free account |
| `BTC_ADDRESS` | Your Bitcoin wallet receive address |

### 3. Add Repository Variable
- `PDF_PRICE_USD` = `4.99` (or any price you want)

### 4. Enable GitHub Pages
Settings → Pages → Source: **GitHub Actions**

### 5. Enable Workflows
Actions tab → enable workflows if prompted.

## How it works

```
Every hour (GitHub Actions cron):
  → Fetch trending topics from Google Trends (15 countries)
  → Generate full guide via Groq AI (Llama 3.3 70B, free)
  → Build styled PDF with images
  → Upload to GitHub Releases
  → Auto-list on Gumroad at your price
  → Update dashboard data

Every 30 min:
  → Sync Gumroad sales
  → Check BTC wallet balance + transactions
  → Update dashboard

Dashboard (GitHub Pages PWA):
  → Live stats: PDFs created, sales, revenue, BTC balance
  → Manual trigger button
  → Installable on any phone (PWA)
```

## Cost

| Component | Cost |
|-----------|------|
| GitHub Actions | **$0** (unlimited on public repos) |
| GitHub Pages | **$0** |
| Groq API (Llama 3) | **$0** (free tier) |
| Google Trends | **$0** |
| Gumroad | **$0** + 10% per sale |
| BTC blockchain.info API | **$0** |
| **Total** | **$0** |
