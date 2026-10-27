# Install prompt for the MyBidMatch daily screening routine

How to use it on the colleague's Mac:

1. Unzip `mybidmatch_screening.zip` into a folder you will keep, e.g. `~/Documents/MyBidMatch`.
2. Open Claude Desktop → Code, start a new session with that folder as the working folder.
3. Paste everything between the two lines below and send it. Stay at the computer: approve the
   prompts, sign in to Gmail when asked, and click **Run now** at the end.

---

Set up the MyBidMatch daily screening routine on this Mac. The project is the current working
folder (it contains `automation/RUNBOOK.md`). Read `automation/SETUP.md`, `automation/RUNBOOK.md`
and `automation/scheduler/SKILL.md` first; they are the reference. Do the steps below in order,
report each result, and stop and tell me if a step fails. Do not change the tools or the RUNBOOK.

1. **Prerequisites.** Check, and install only what is missing:
   - Homebrew (`brew -v`). If it is missing, stop and ask me to install it from https://brew.sh.
   - `brew install poppler node` (for `pdftotext`, `node`, `npx`).
   - Python packages for the tools, which run as `python3 -I` (user site-packages are ignored, so
     never use `pip --user`): `python3 -m pip install openpyxl python-docx`, adding
     `--break-system-packages` only if pip reports "externally-managed-environment".
   - Playwright browser: `npx -y playwright install chrome`.
   - Verify all of: `pdftotext -v`, `node -v`, `textutil -help` (macOS built-in),
     `python3 -I -c "import openpyxl, docx; print('ok')"`.
     If the last check fails (pip may silently fall back to the user site, which `-I` ignores):
     `brew install python`, make sure `which python3` now points to Homebrew's python3, then
     `python3 -m pip install --break-system-packages openpyxl python-docx` and check again.
2. **Settings.** Write `automation/config.json` as
   `{"recipient": "alimul@inovisolutions.com", "start_date": "<date>"}`, where `<date>` is the
   alert date (YYYY-MM-DD) of the NEWEST MyBidMatch alert found in step 3 (fill it in after step 3;
   today's date if there is none). That way the first supervised run processes one real alert and
   every tool gets approved, while older backlog is skipped.
   Overwrite `automation/state/processed.json` with `{"processed": []}` (state from another machine
   must not carry over). Create `runs/` if it is missing; if it holds run folders from another
   machine, move them to `runs/_old_from_other_machine/` instead of deleting them.
3. **Gmail.** Check the Gmail connector is connected (a Gmail search must work). If it is not,
   tell me to connect it in Settings → Connectors → Gmail and wait. It must be the account that
   receives the alerts from `noreply@mybidmatch.com` (alimul@inovisolutions.com): run the search
   `from:noreply@mybidmatch.com newer_than:14d` and show me how many alerts it finds and the newest
   date. Do not send any email in this step.
4. **Playwright.** Confirm the `playwright-headless` MCP server from `.mcp.json` is enabled for
   this project (`.claude/settings.local.json` has `"enabledMcpjsonServers": ["playwright-headless"]`).
   Open https://sam.gov in it once and report the page title, to prove the browser works.
5. **Tool smoke test.** Run `python3 -I automation/tools/build_tracker.py` with no arguments and
   confirm it prints its usage (no import errors). Do the same for
   `automation/tools/mybidmatch.py` and `automation/tools/sam_download.py`.
6. **Scheduled task.** Create a local scheduled task with the scheduled-tasks tool:
   - task id `mybidmatch-daily-screening`, title "MyBidMatch daily screening"
   - cron `0 9 * * *` (every day at 9:00 AM local time)
   - prompt: the body of `automation/scheduler/SKILL.md` (everything after the front matter), with
     `<PROJECT_DIR>` replaced by the absolute path of this folder.
   If a task with that id already exists, update it instead of creating a second one. Show me the
   saved task (id, schedule, working folder, first lines of the prompt).
7. **Finish.** Tell me to open Scheduled → "MyBidMatch daily screening" → **Run now** while I am at
   the computer and to choose "Always allow" for every tool prompt, so the 9 AM runs are not
   blocked. If that run found no alert to process (nothing was downloaded or emailed), tell me to
   repeat Run now under supervision the next morning after an alert arrives. Remind me that at
   9 AM the Mac must be on and AWAKE with Claude Desktop open: turn on Claude Desktop's
   "Keep computer awake" setting, and do not leave the lid closed (unless an external display and
   power are connected). Also: keep `MyBidMatch_Screening_Tracker.xlsx` closed overnight.

Never enter passwords, never send email during setup, and never edit anything outside this folder
except the scheduled task and the package installs above.

---
