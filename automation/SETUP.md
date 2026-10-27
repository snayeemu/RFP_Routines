# MyBidMatch daily screening — setup on a new Mac

Quickest way: follow `INSTALL_PROMPT.md` in the project root (Claude does these steps for you).

This package runs a Claude Desktop scheduled task every morning. The task reads the MyBidMatch
alert in Gmail, downloads every solicitation, screens it against Inovi's four profile PDFs, adds
a dated tab to `MyBidMatch_Screening_Tracker.xlsx` and emails an HTML summary.

## 1. Prerequisites (one time)

In Terminal:

```
# Homebrew (skip if `brew -v` works): https://brew.sh
brew install poppler node
python3 -m pip install openpyxl python-docx
# if pip says "externally-managed-environment", rerun it with --break-system-packages
# (do NOT use --user: the tools run as `python3 -I`, which ignores user packages)
npx -y playwright install chrome
pdftotext -v && node -v && python3 -I -c "import openpyxl, docx; print('ok')"
```

All checks must pass. Then install the Claude Desktop app and sign in to Claude.

## 2. Copy the project

Unzip `mybidmatch_screening.zip` into a folder you will keep, e.g. `~/Documents/MyBidMatch`.
That folder is `<PROJECT_DIR>` below. Do not move it later; if you do, update the task (step 5).

## 3. Settings

Edit `<PROJECT_DIR>/automation/config.json`:

- `recipient`: the email address that should get the daily summary.
- `start_date`: today's date (`YYYY-MM-DD`). Older alerts are ignored, so the first run does not
  work through two weeks of backlog.

## 4. Connect Gmail

In Claude Desktop: Settings → Connectors → Gmail → Connect, and sign in with the Google account
that RECEIVES the MyBidMatch alerts (from noreply@mybidmatch.com). Emails are sent from it too.

## 5. Create the scheduled task

1. Claude Desktop → Code → Scheduled → New task.
2. Name: `MyBidMatch daily screening`.
3. Folder: `<PROJECT_DIR>`.
4. Prompt: paste the contents of `automation/scheduler/SKILL.md` (from the line
   "You are the daily MyBidMatch ..." to the end), replacing `<PROJECT_DIR>` with the real path.
5. Schedule: daily at 9:00 AM.

## 6. First run (approve tools)

Click **Run now** and stay at the computer: approve Gmail, Bash, file and Playwright prompts with
"Always allow" so later unattended runs are not blocked. When it finishes, check the email and the new tab in
`MyBidMatch_Screening_Tracker.xlsx`.

## Daily operation

- The Mac must be on and awake (Claude Desktop "Keep computer awake" on, lid open) with Claude
  Desktop open at 9 AM; a missed run is caught up on the next run
  (alerts from the last 14 days that are not yet processed).
- Close the tracker workbook in Excel overnight; if it is open, the run waits and then emails
  without adding the tab (the email says so).
- Logs: `runs/<date>_<id>/run_log.md`. State: `automation/state/processed.json`.
- To re-run a day: delete its entry in `processed.json` and its `runs/<date>_<id>/` folder, then
  Run now.
