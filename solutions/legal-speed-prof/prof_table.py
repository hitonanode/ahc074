#!/usr/bin/env python3
"""Tables of the request profile of a legal-speed-prof run (per case means of the err files).

usage: prof_table.py RUN [BASE_RUN]
  RUN: run-id (or a path to runs/<run-id>) of legal-speed-prof; BASE_RUN: the same compare's
  legal-tie-fast run, for the time added by the scopes (req_sec of both).
"""
import glob
import os
import re
import sys

ROOT = '/home/sato/ahc074/runs'
LINE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*) = (-?[0-9.eE+-]+|nan|inf)$')


def load(run):
    d = run if os.path.isdir(run) else os.path.join(ROOT, run)
    cases = {}
    for f in glob.glob(os.path.join(d, 'err', '*.txt')):
        v = {}
        for line in open(f):
            m = LINE.match(line.strip())
            if m:
                try:
                    v[m.group(1)] = float(m.group(2))
                except ValueError:
                    pass
        cases[os.path.basename(f)[:-4]] = v
    return cases


def mean(cases, key):
    xs = [c[key] for c in cases.values() if key in c]
    return sum(xs) / len(xs) if xs else float('nan')


def main():
    cases = load(sys.argv[1])
    n = len(cases)
    req = mean(cases, 'req_sec') * 1000
    print(f'cases {n}  req_ms {req:.1f}  phase_sum_ms {mean(cases, "phase_sum_ms"):.1f}  '
          f'process_inc {mean(cases, "cfprof_process_inc"):.1f}  overhead_est_ms {mean(cases, "cfprof_overhead_ms"):.1f}  '
          f'scope_ns {mean(cases, "cfprof_scope_ns"):.2f}  scopes {mean(cases, "cfprof_scopes"):.0f}')
    if len(sys.argv) > 2:
        base = load(sys.argv[2])
        common = sorted(set(base) & set(cases))
        d = [cases[s]['req_sec'] - base[s]['req_sec'] for s in common if 'req_sec' in cases[s] and 'req_sec' in base[s]]
        print(f'req_ms of the base {1000 * sum(base[s]["req_sec"] for s in common) / len(common):.1f}  '
              f'added by the scopes {1000 * sum(d) / len(d):+.1f} ms')
    print('\nphases of process (ms per case, calls per case, ms per call x1000 = us)')
    phases = sorted({k[6:-3] for c in cases.values() for k in c if k.startswith('phase_') and k.endswith('_ms') and k != 'phase_sum_ms'},
                    key=lambda p: -mean(cases, f'phase_{p}_ms'))
    for p in phases:
        ms, calls = mean(cases, f'phase_{p}_ms'), mean(cases, f'phase_{p}_calls')
        print(f'  {p:12s} {ms:8.1f} ms {100 * ms / req:5.1f}%  calls {calls:8.0f}  {1000 * ms / calls if calls else 0:8.1f} us/call')
    print('\nfunctions (inclusive ms, exclusive ms, calls, ns per call inclusive)')
    names = sorted({k[7:-4] for c in cases.values() for k in c if k.startswith('cfprof_') and k.endswith('_inc')},
                   key=lambda p: -mean(cases, f'cfprof_{p}_exc'))
    for p in names:
        inc, exc, calls = mean(cases, f'cfprof_{p}_inc'), mean(cases, f'cfprof_{p}_exc'), mean(cases, f'cfprof_{p}_calls')
        print(f'  {p:14s} inc {inc:8.1f}  exc {exc:8.1f} {100 * exc / req:5.1f}%  calls {calls:10.0f}  {1e6 * inc / calls if calls else 0:9.0f} ns')
    print('\ncounters')
    for k in ['cf_value_hits', 'cf_value_misses', 'f2_memo_hits', 'f2_memo_misses', 'tail_hits', 'eject_trials',
              'eject_accepts', 'neutral_total', 'neutral_accepted', 'ns_rounds', 'ns_plan_calls', 'f2_plan_screens',
              'f2_plan_wins', 'f2_plan_skipped', 'post_candidate_calls', 'post_alternate', 'interleave_trials',
              'interleave_selected', 'chain_trials', 'chain_selected', 'value_seed_trials', 'value_seed_accepts',
              'tie_decisions', 'tie_switches', 'merge_trials', 'merge_saved', 'total_moves']:
        print(f'  {k:22s} {mean(cases, k):12.1f}')


if __name__ == '__main__':
    main()
