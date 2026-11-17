# Giving Tree donor apps v2 (2026-11-17)

Folder: giving-tree-donor/v2/
- donor_worker.py, start-mac.command, start-windows.bat, .env.example : Mac + PC helper
- web/ : the phone app (installable web app, "PWA"): index.html, manifest.json, sw.js, icons
- tools/make_icons.py : makes the icons again if you want to change them

## What is REAL and what is SPEC (honest)
REAL, tested 2026-11-17 against the live server with test donors (all marked zz-test, now set to "left"):
- donor_worker.py: claimed a job, did it, sent the answer back; pause, resume, share change and leave all worked. Tested in the Linux sandbox on Woz's Mac, NOT yet on a real macOS or real Windows machine.
- The phone web app: sign-up form (reaches the live signup function), token save, consent, share slider, Start, "Helping" status, 8 real jobs done, Pause, Leave (wipes the token). Tested in desktop Chrome pretending to be a phone, NOT yet on a real iPhone or Android.
SPEC / UNTESTED: install steps on a real iPhone and Android; start-windows.bat (never run on Windows); the 30% battery floor on real laptops/phones.
One server bug found and fixed: donor_set used to drop a donor to 1% share whenever pause was pressed without a share number. Fixed (migration donor_set_null_share_fix).
Jobs are simple rules (tag = top words, summarize = first sentence(s), count = words/chars/sentences). No AI model runs on phones. The Mac/PC helper uses your local Ollama if it finds one; otherwise the same rules.

## The most important limit (phones)
A web app only works while it is OPEN and ON SCREEN. iPhone and Android freeze web pages when you lock the screen or switch apps, so helping stops then. There is no background helping on iPhone at all (Apple does not allow it for web apps). Android is the same unless a real Android app is built later. Best use: plugged in, screen on, app open, tick "Keep the screen on". It uses some battery and data; the app pauses below 30% battery on Android Chrome (iPhone does not tell web apps the battery level, so there is no battery pause on iPhone).

## Before anyone can test: the app must live at an https address
Phones will not install a web app from a file or from this Mac. It has to be hosted at an https address. Cheapest options:
1. GitHub Pages: free, about 10 minutes. Needs Woz's OK because it means creating a public repo and publishing. Address looks like https://<name>.github.io/giving-tree/.
2. littledeerlodge.com (or a subfolder like littledeerlodge.com/giving-tree/): free if the site host lets us add files. Needs Woz's OK (his public site).
3. Cloudflare Pages or Netlify drag-and-drop: free, needs a free account Woz creates. Needs Woz's OK.
Not workable: the claude.ai private artifact page (it blocks calls to outside servers), and Supabase Storage (it serves web pages as plain text).
Nothing has been published, pushed or sent. To host, copy everything inside web/ (7 files) into one folder on the host.
Anyone who finds the page can sign up, but Woz still approves each person (approve_giving_tree_donor) before any token exists.

## Wife (iPhone) installs
1. Woz sends her the app address (after he OKs hosting). Open it in SAFARI (not inside a text-message preview or Chrome).
2. Tap the Share button (square with an arrow), scroll, tap "Add to Home Screen", tap Add.
3. Open "Giving Tree" from the home screen. Fill the sign-up form (name, email, share %, tick the box), tap Sign me up.
4. Woz approves her and sends her the token (starts with gtd_). She opens the app, pastes it, taps Save token, ticks I agree, taps Start helping.
5. Keep the app open and the screen on; plug in. To stop: Pause, Stop helping, or Leave Giving Tree (wipes the token).

## Friend (Android) installs
1. Open the app address in Chrome. Tap the three dots, then "Install app" (or "Add to Home screen").
2. Same steps 3-5 as above. Ticking "Keep the screen on" helps; the app also pauses itself under 30% battery when not charging.

## Mac install (helper that can run all the time)
1. Needs Python 3 (python.org) once. Copy the v2 folder to the Mac.
2. Double-click start-mac.command (first time: right-click, Open). It installs "requests", then opens .env for you.
3. Paste the token after GT_DONOR_TOKEN= , save, double-click start-mac.command again. It shows the consent text; type agree.
4. Stop: Ctrl-C or close the window. Other commands (Terminal in this folder): python3 donor_worker.py --share 25 | --pause | --resume | --leave
   --leave tells the server you left and wipes your token and consent from the Mac.

## PC (Windows) install
1. Needs Python 3 from python.org (tick "Add python.exe to PATH").
2. Double-click start-windows.bat. It installs "requests", opens .env in Notepad: paste the token after GT_DONOR_TOKEN= , save, double-click again. Type agree.
3. Same flags as Mac, e.g. py donor_worker.py --leave. SmartScreen may warn about an unsigned .bat: "More info", "Run anyway".

## Safety rules built in
One personal token per donor (no owner secrets in these files). Only job kinds tag, summarize and count; the server also filters. Share percent enforced by the server (10-minute duty cycle) and by the app. No file, contact, photo, camera, mic or location access. Leave wipes the token. The publishable key in the files is public by design and grants nothing without a donor token.

## Not built yet
Real Android app (background service) after about 10 real donors ask; an in-browser model (WebLLM); a donor dashboard; signed Mac .app and Windows .exe installers so no Python is needed.
