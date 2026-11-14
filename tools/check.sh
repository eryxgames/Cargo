#!/bin/sh
# Run every check on cargo.py. Usage: tools/check.sh [quick]
# quick: a few seeds; default: the full matrix used for the 1.1.0 release.
cd "$(dirname "$0")/.." || exit 1
T=tools
PY=${PYTHON:-python3}
if [ "$1" = "quick" ]; then SEEDS="1 2"; WIDTHS="80 40 36"; N=600; else SEEDS="1 2 3 4"; WIDTHS="100 80 60 50 44 40 36"; N=1500; fi
fail=0

echo "== wrong-object references"
$PY $T/attrlint.py cargo.py | tail -1

echo "== story machinery (stats forced, real chapter code)"
$PY $T/story_probe.py cargo.py > /tmp/cargo-probe.txt; grep -E "REACHED|BLOCKED|!" /tmp/cargo-probe.txt
grep -q "BLOCKED" /tmp/cargo-probe.txt && fail=1

echo "== damaged and hostile save / captain files"
$PY $T/test_files.py cargo.py | tail -1 || fail=1

echo "== save / load round trips"
for s in $SEEDS; do $PY $T/roundtrip.py cargo.py $s 1200 800 | $PY -c "
import json,sys
r=json.load(sys.stdin)
ok=r.get('identical') and r.get('captain_ok') and not r.get('stale_refs_to_old_game') and 'traceback' not in r
print('  seed', r['seed'], 'ok' if ok else 'FAIL', r.get('traceback','')[-300:])
sys.exit(0 if ok else 1)" || fail=1; done

echo "== random play at each width (crashes, lines wider than the screen)"
for w in $WIDTHS; do for s in $SEEDS; do $PY $T/infuzz.py cargo.py $w $N $s | $PY -c "
import json,sys
r=json.load(sys.stdin)
ok=not r['traceback'] and not r['overflow_kinds']
print('  cols', r['cols'], 'seed', r['seed'], 'inputs', r['inputs'], 'ok' if ok else 'FAIL', (r['traceback'] or '')[-300:], r['overflow'][:2] if r['overflow_kinds'] else '')
sys.exit(0 if ok else 1)" || fail=1; done; done

echo "== playthroughs to each ending (real commands; a bankrupt bot is a lost game, not a bug)"
for goal in trade combat discovery discovery2; do for s in $SEEDS; do $PY $T/bot.py cargo.py $goal $s 1500 --save-every=9 | $PY -c "
import json,sys
r=json.load(sys.stdin)
crash='traceback' in r
print('  %-10s seed %s: %s at turn %s, %s loads %s' % (r['goal'], r['seed'], r.get('ending') or r.get('end'), r.get('turn'), r.get('loads'), 'CRASH '+r['traceback'][-300:] if crash else ''))
sys.exit(1 if crash else 0)" || fail=1; done; done

echo "== story file matches the code, and has no new findings"
$PY tools/cargo_story.py check || fail=1
$PY tools/build_story.py --check || fail=1
$PY storykit/validate.py story/saga.json --baseline story/findings-baseline.json > /tmp/cargo-validate.txt; tail -3 /tmp/cargo-validate.txt
grep -q "baseline: 0 new" /tmp/cargo-validate.txt || fail=1

echo "== story file agrees with the game during play (recorded traces)"
mkdir -p story/traces
for goal in trade combat discovery discovery2; do for s in $SEEDS; do
  $PY tools/bot.py cargo.py $goal $s 1500 --trace=story/traces/$goal-$s.jsonl > /dev/null || fail=1
done; done
$PY storykit/replay.py story/cargo1.story.json story/traces/*.jsonl --json story/cargo1.replay.json > /tmp/cargo-replay.txt; tail -1 /tmp/cargo-replay.txt
grep -q "agree on every recorded verdict" /tmp/cargo-replay.txt || fail=1

[ $fail = 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
