"""Regression test: Portuguese-field purification removes leaks from the script API.

Run with the standard library only:
    python test_purify.py        # exit 0 = pass, exit 1 = fail
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import podcast_generator as pg

FAILURES = []


def check(name, got, must_have=(), must_missing=()):
    for s in must_have:
        if s not in got:
            FAILURES.append("%s: missing %r in %r" % (name, s, got))
    for s in must_missing:
        if s in got:
            FAILURES.append("%s: leaked %r in %r" % (name, s, got))


# 1. Leak mixed into target text is removed.
out = pg._purify_target('Bom dia 你好')
check("leak-plain", out, (), ('你好',))

# 2. Leak inside highlight markers is removed (empty markers go too).
out = pg._purify_target('Oi Rafael, hoje vamos falar sobre a **cidade**. 你好')
check("leak-in-highlight", out, (), ('你好', '****'))

# 3. The brand name survives purification untouched.
brand = 'Velocity Portuguese. Oi Rafael, hoje vamos falar sobre a **cidade**.'
if pg._purify_target(brand) != brand:
    FAILURES.append("brand: damaged -> %r" % pg._purify_target(brand))

# 4. Clean input passes through unchanged.
clean = 'Oi Rafael, hoje vamos falar sobre a **cidade**.'
if pg._purify_target(clean) != clean:
    FAILURES.append("clean-passthrough: changed -> %r" % pg._purify_target(clean))

# 5. Transliterator converts the test sample.
tr = pg.to_accurate_translit('Bom dia')
if tr != 'Bom dia':
    FAILURES.append('translit-passthrough: %r' % tr)

# 5b. Transliterator never returns empty on real content.
tr2 = pg.to_accurate_translit(clean)
if len(tr2) < 5:
    FAILURES.append('translit-empty: %r' % tr2)
# 6. End-to-end fragment of the generate_script guarantee loop.
turn = {"target": 'Oi Rafael, hoje vamos falar sobre a **cidade**.', "translit": ""}
trg = pg._purify_target(turn.get("target", ""))
turn["target"] = trg
check("guarantee-writeback", turn["target"], (), ('你好', '****'))

# 7. Auto-highlight keeps existing markers or adds one.
hl = pg.auto_highlight_target(clean)
if "**" not in hl:
    FAILURES.append("highlight: no markers in %r" % hl)

# 8. Karaoke tokenizer yields tokens that rebuild the text.
toks = pg.karaoke_tokens_for_text(trg or clean)
if not toks:
    FAILURES.append("karaoke: no tokens")
elif "".join(toks).replace(" ", "") != (trg or clean).replace("**", "").replace(" ", ""):
    FAILURES.append("karaoke: rebuild mismatch %r" % toks)

# 9. Fallback turns address the OTHER host, never self (except self-introduction).
import json as _json
import re as _re
_fb = _json.loads((Path(__file__).resolve().parent.parent / "fleet_cache.json").read_text(encoding="utf-8"))["Portuguese"]["fallback"]
_addr_bad = []
for _i, _t in enumerate(_fb):
    _en = _t.get("english", "") or ""
    _spk = _t.get("speaker", "")
    _own = "Ana" if _spk == "Host2" else "Rafael"
    _other = "Rafael" if _spk == "Host2" else "Ana"
    _el = _en.lower()
    if _re.search(r"%s" % _own.lower(), _el) and not _re.search(r"(i'm|i am|this is|my name is) %s" % _own.lower(), _el):
        _addr_bad.append((_i, _en))
    if _i < 2 and _other.lower() not in _el:
        _addr_bad.append((_i, "intro-missing-other: " + _en))
if _addr_bad:
    FAILURES.append('addressing: %r' % (_addr_bad,))

if FAILURES:
    print("FAIL %d" % len(FAILURES))
    for f in FAILURES:
        print(" -", f)
    sys.exit(1)
print("PASS")
