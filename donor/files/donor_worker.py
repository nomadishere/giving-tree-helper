#!/usr/bin/env python3
"""Giving Tree donor worker v2 (Mac + Windows + Linux). Needs Python 3.8+ and `requests`.

What it does, in plain words:
  - Reads ONE personal donor token from a local .env file (GT_DONOR_TOKEN=gtd_...). Never an owner secret.
  - Asks the server for a small public-safe job (kinds: tag, summarize, count), does it, sends the answer back.
  - Share percent is enforced twice: by the server (10 minute duty cycle in donor_claim) and here (rest between jobs).
  - Pause / resume / leave are command-line flags (see --help) and Ctrl-C stops it at any time.
  - Touches no personal files, contacts, photos, camera or mic. Talks only to the Supabase address below and,
    if you have it installed, your own local Ollama (optional, never required).
Status: REAL on the claim/done flow (tested 2026-11-17 against the live server with a test donor).
"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("This needs the 'requests' package. Run:  python3 -m pip install requests   (Windows:  py -m pip install requests)")

BASE = "https://wwqjoagdnclaylllzcut.supabase.co"
RPC = BASE + "/rest/v1/rpc/"
PUBLISHABLE = "sb_publishable_AVIpI00DFiYwugP16-wMWQ_qENLObrc"  # public by design; grants nothing without a donor token
PUBLIC_KINDS = {"tag", "summarize", "count"}   # belt and braces; the server filters too
HOME = Path.home() / ".giving_tree"
CONSENT = HOME / "consent.json"
LOG = HOME / "donor_worker.log"
HERE = Path(__file__).resolve().parent
ENV_PATHS = [HERE / ".env", HOME / ".env"]
CONSENT_TEXT = ("Giving Tree lends spare time on this computer, at the share percent you pick, to small harmless "
                "text jobs (tag, summarize, count). It never reads your files, photos, contacts, messages or accounts. "
                "No money moves. You can pause or leave at any time.")

def log(m):
    try:
        HOME.mkdir(mode=0o700, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + m + "\n")
    except Exception:
        pass

# ---------- .env (token) ----------
def env_path():
    for p in ENV_PATHS:
        if p.exists():
            return p
    return ENV_PATHS[0]

def read_env():
    out = {}
    for p in ENV_PATHS:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return out

def get_token():
    t = os.environ.get("GT_DONOR_TOKEN") or read_env().get("GT_DONOR_TOKEN", "")
    return t if t.startswith("gtd_") else ""

def wipe_token():
    for p in ENV_PATHS:
        if p.exists():
            lines = [l for l in p.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("GT_DONOR_TOKEN")]
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")

# ---------- server ----------
def rpc(fn, body):
    r = requests.post(RPC + fn, json=body, timeout=60,
                      headers={"apikey": PUBLISHABLE, "Authorization": "Bearer " + PUBLISHABLE, "Content-Type": "application/json"})
    if r.status_code >= 400:
        raise RuntimeError("server said %s: %s" % (r.status_code, r.text[:160]))
    return r.json() if r.text.strip() else None

# ---------- jobs: simple rules (same ideas as the phone app), optional local Ollama ----------
STOP = set("the a an and or but if then of to in on at for with from by is are was were be been being it its this that these those as not no so than too very can will just into over under about after before while which who whom what when where why how their there they them you your we our he she his her i me my also more most some any each other such only own same".split())

def words_of(text):
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text)

def do_count(text):
    w = len(text.split()); s = len([x for x in re.split(r"[.!?]+(?:\s|$)", text) if x.strip()])
    return "words=%d chars=%d sentences=%d" % (w, len(text), s)

def do_tag(text):
    freq, first = {}, {}
    for i, w in enumerate(words_of(text.lower())):
        if len(w) < 4 or w in STOP:
            continue
        freq[w] = freq.get(w, 0) + 1; first.setdefault(w, i)
    top = sorted(freq, key=lambda k: (-freq[k], first[k]))[:3]
    return ", ".join(top) if top else "misc"

def do_summarize(text):
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
    out = []
    for s in sents:
        if len((" ".join(out + [s])).split()) > 25:
            break
        out.append(s)
    res = " ".join(out) if out else " ".join(text.split()[:25])
    return res[:400]

def ollama_ok():
    try:
        return requests.get("http://localhost:11434/api/tags", timeout=1.5).status_code == 200
    except Exception:
        return False

def ollama_run(kind, text, model):
    prompts = {"tag": "Give 3 short lowercase tags (comma separated, no other words) for this text: ",
               "summarize": "Summarize in one plain sentence (max 25 words): ",
               "count": "Count the words in this text and reply with only the number: "}
    r = requests.post("http://localhost:11434/api/generate", timeout=180,
                      json={"model": model, "prompt": prompts[kind] + text, "stream": False, "options": {"num_predict": 120}})
    return r.json()["response"].strip()

def run_job(kind, text, use_ollama, model):
    text = (text or "")[:4000]
    if use_ollama and kind != "count":
        try:
            return ollama_run(kind, text, model), "ollama:" + model
        except Exception as e:
            log("ollama failed, using rules: %s" % str(e)[:100])
    return {"tag": do_tag, "summarize": do_summarize, "count": do_count}[kind](text), "rules-v1"

# ---------- power ----------
def battery_ok(floor=30):
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
            if "AC Power" in out: return True
            m = re.search(r"(\d+)%", out); return int(m.group(1)) >= floor if m else True
        if sys.platform.startswith("win"):
            import ctypes
            class S(ctypes.Structure):
                _fields_ = [("AC", ctypes.c_byte), ("Flag", ctypes.c_byte), ("Pct", ctypes.c_byte), ("Sav", ctypes.c_byte), ("Life", ctypes.c_ulong), ("Full", ctypes.c_ulong)]
            s = S()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
                if s.AC == 1 or s.Pct == 255: return True
                return s.Pct >= floor
    except Exception:
        pass
    return True

# ---------- consent ----------
def ensure_consent(auto_yes=False):
    if CONSENT.exists(): return True
    print("\n" + CONSENT_TEXT + "\n")
    ans = "agree" if auto_yes else input("Type  agree  to start, anything else to cancel: ").strip().lower()
    if ans != "agree": print("Not started."); return False
    HOME.mkdir(mode=0o700, exist_ok=True)
    CONSENT.write_text(json.dumps({"agreed_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "version": "v1"}))
    log("consent"); return True

# ---------- main loop ----------
def main():
    ap = argparse.ArgumentParser(description="Giving Tree donor worker (public-safe jobs only)")
    ap.add_argument("--share", type=int, help="share percent 1-100 (also saved on the server)")
    ap.add_argument("--pause", action="store_true", help="tell the server to pause you, then exit")
    ap.add_argument("--resume", action="store_true", help="tell the server to resume you, then exit")
    ap.add_argument("--leave", action="store_true", help="leave Giving Tree: server forgets your token, wipes it here")
    ap.add_argument("--once", action="store_true", help="do at most one job then exit (for testing)")
    ap.add_argument("--no-rest", action="store_true", help="testing only: skip the share-percent rest between jobs")
    ap.add_argument("--yes", action="store_true", help="testing only: accept the consent text without typing")
    ap.add_argument("--no-ollama", action="store_true", help="never use a local Ollama, rules only")
    ap.add_argument("--model", default="llama3.2:3b")
    a = ap.parse_args()

    token = get_token()
    if not token:
        sys.exit("No donor token yet. After you are approved you get a token that starts with gtd_ . Put it in the .env file next to this script as:\nGT_DONOR_TOKEN=gtd_...")

    if a.leave:
        try: rpc("donor_set", {"p_token": token, "p_paused": True, "p_share": None, "p_leave": True})
        except Exception as e: print("note: could not tell server (%s); wiping token here anyway" % e)
        wipe_token()
        try: CONSENT.unlink()
        except Exception: pass
        log("left"); print("You left Giving Tree. Token and consent wiped from this computer. Thank you."); return
    if a.pause or a.resume:
        rpc("donor_set", {"p_token": token, "p_paused": bool(a.pause), "p_share": a.share, "p_leave": False})
        print("paused" if a.pause else "resumed"); return
    if a.share is not None:
        rpc("donor_set", {"p_token": token, "p_paused": False, "p_share": a.share, "p_leave": False})
    share = max(1, min(100, a.share if a.share is not None else 10))

    if not ensure_consent(a.yes): return
    use_ollama = (not a.no_ollama) and ollama_ok()
    print("Giving Tree helping at %d%%. Engine: %s. Press Ctrl-C to stop." % (share, ("local Ollama " + a.model) if use_ollama else "simple rules"))
    done = 0
    try:
        while True:
            try:
                if not battery_ok():
                    print("paused: battery low"); time.sleep(30); continue
                jobs = rpc("donor_claim", {"p_token": token})
                if not jobs:
                    if a.once: print("no job waiting (or you are paused / at your share limit)"); return
                    print("idle, waiting for jobs..."); time.sleep(15); continue
                j = jobs[0]
                if j["kind"] not in PUBLIC_KINDS:
                    log("skipped non-public kind"); rpc("donor_done", {"p_token": token, "p_id": j["id"], "p_model": "none", "p_result": "skipped: not a public kind", "p_ok": False}); continue
                t0 = time.time()
                try: out, model = run_job(j["kind"], j["input"], use_ollama, a.model); ok = True
                except Exception as e: out, model, ok = "error: " + str(e)[:200], "none", False
                rpc("donor_done", {"p_token": token, "p_id": j["id"], "p_model": model, "p_result": out, "p_ok": ok})
                done += 1; print("job %s (%s) %s -> %s" % (j["id"], j["kind"], "ok" if ok else "failed", out[:60]))
                if a.once: return
                busy = max(time.time() - t0, 1.0)
                if not a.no_rest: time.sleep(min(busy * (100 - share) / max(share, 1), 600))
            except KeyboardInterrupt: raise
            except Exception as e:
                log("loop error %s" % str(e)[:200]); print("error, retrying in 30s: %s" % str(e)[:100])
                if a.once: sys.exit(1)
                time.sleep(30)
    except KeyboardInterrupt:
        print("\nStopped. %d job(s) done this time. Run again any time." % done)

if __name__ == "__main__":
    main()
