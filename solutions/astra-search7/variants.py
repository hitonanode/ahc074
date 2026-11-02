#!/usr/bin/env python3
"""基準から assign_windows 内だけを変更した実験版を生成する。"""
from pathlib import Path
import argparse,json
from double import double
from group import group
from guided import guided
from restart import restart
from rescue import rescue
from batch import batch
from prior import transfer_prior,window_prior
from protect import protect
from globalmemo import globalmemo
from sources import sources
from unified import unified
from direct import direct
p=argparse.ArgumentParser()
p.add_argument('name')
p.add_argument('--direct-screen',action='store_true')
p.add_argument('--unified',action='store_true')
p.add_argument('--kind95',action='store_true')
p.add_argument('--window-rate',type=float,default=0.6)
p.add_argument('--sources',type=int,default=0)
p.add_argument('--constant-temp',type=float,default=-1)
p.add_argument('--global-memo',type=int,default=0)
p.add_argument('--ignore-loss',type=int,default=0)
p.add_argument('--window-weight',type=int,default=0)
p.add_argument('--transfer-loss',type=int,default=0)
p.add_argument('--tabu',type=int,default=4)
p.add_argument('--batch',type=int,default=0)
p.add_argument('--rescue',type=int,default=0)
p.add_argument('--restart',type=float,default=0)
p.add_argument('--restart-interval',type=int,default=4096)
p.add_argument('--temperature',type=float,default=1)
p.add_argument('--guided',type=int,default=0)
p.add_argument('--guide-tolerance',type=int,default=1800)
p.add_argument('--guide-all',action='store_true')
p.add_argument('--large-loss',type=int,default=3)
p.add_argument('--group',type=int,default=0)
p.add_argument('--double',type=int,default=0)
p.add_argument('--exchange',type=int,default=0,help='色付き汎用窓交換の頻度1/n')
p.add_argument('--enumerate',action='store_true')
p.add_argument('--cross-rate',type=int,default=16)
p.add_argument('--map-stall',type=int,default=256)
p.add_argument('--climb-stall',type=int,default=512)
p.add_argument('--cross-adapt',type=int,default=0)
p.add_argument('--cross-empty',action='store_true')
p.add_argument('--transfer-rank',type=int,default=0)
a=p.parse_args();h=Path(__file__).resolve().parent
s=(h.parent/'as6-cap38/main.cpp').read_text();l=s.index('WindowStats assign_windows(');r=s.index('// kBitLanes',l);t=s[l:r]
t=t.replace('kMapStall = 256, kClimbStall = 512',f'kMapStall = {a.map_stall}, kClimbStall = {a.climb_stall}')
t=t.replace('kTabuAccepted = 4',f'kTabuAccepted = {a.tabu}')
t=t.replace('rng.mod(16)==0',f'rng.mod({a.cross_rate})==0')
if a.cross_adapt:
    t=t.replace('    auto propose = [&](Move& mv) {', '    int stagnant_tries = 0;\n    auto propose = [&](Move& mv) {\n        ++stagnant_tries;')
    t=t.replace(f'rng.mod({a.cross_rate})==0', f'rng.mod(stagnant_tries < {a.cross_adapt} ? 64 : 4)==0')
    t=t.replace('    auto apply_move = [&](const Move& mv) {', '    auto apply_move = [&](const Move& mv) {\n        stagnant_tries = 0;')
if a.cross_empty:
    needle2='        const bool cross_move ='
    i=t.index(needle2);j=t.index('\n',i)
    t=t[:i]+"""        // When the same-group row is exhausted, spend the next proposal on a
        // compound exchange from this window. The state and exact objective are shared.
        if (swindow && selected.size() == unsigned(need) && window_epoch[a] != epoch) {
            window_options[a] = prepare_windows(a,ea); window_epoch[a] = epoch;
        }
        const bool cross_move = swindow && counts[ea] >= 2 && selected.size() == unsigned(need) &&
            (!(window_options[a][0]|window_options[a][1]) || rng.mod(RATE)==0);""".replace('RATE',str(a.cross_rate))+t[j:]
if a.exchange:
    t=t.replace('12352 + 2 *','24640 + 2 *').replace('16384 + 2*','32768 + 2*')
    t=t.replace('8256 + 64 * std::min(a, b) + std::max(a, b)', '8256 + 4 * (64 * std::min(a,b) + std::max(a,b)) + int(pol>>std::min(a,b)&1) + 2*int(pol>>std::max(a,b)&1)')
    old='''            else if (mv.transfer >= 0) reverse_key = 24640 + 2 * (ne * mv.a + mv.ea) + ((mv.oldpol >> mv.a) & 1);'''
    assert t.count(old)==2
    t=t.replace(old,old+'''
            else if (mv.kind >= 3) reverse_key = 8256 + 4*(64*std::min(mv.a,mv.b)+std::max(mv.a,mv.b))
                + int(mv.oldpol>>std::min(mv.a,mv.b)&1) + 2*int(mv.oldpol>>std::max(mv.a,mv.b)&1);''')
    needle='    auto propose = [&](Move& mv) {'
    helper='''    std::array<unsigned,4096> exchange_epoch{};
    std::array<unsigned char,4096> exchange_options{};
    long long exchange_rows = 0, exchange_samples = 0, exchange_accepts = 0;
    // Delete both windows before testing all four color combinations. Only the
    // two changed sheet-pair directions need rebuilding for each selected pair.
    auto prepare_exchange = [&](int a, int b, int ea, int eb) {
        std::array<int,4> losses{};
        unsigned options = 15;
        const u64 ma = (mask[ea] & ~(1ULL<<a)) | (1ULL<<b);
        const u64 mb = (mask[eb] & ~(1ULL<<b)) | (1ULL<<a);
        const uint32_t keep = ~uint32_t(fwd[ea]|rev[ea]|fwd[eb]|rev[eb]);
        for (int p : selected) {
            const u64 qa = pairs.diff[p] & ma, qb = pairs.diff[p] & mb;
            for (unsigned codes=options; codes; codes &= codes-1) {
                const int c = __builtin_ctz(codes);
                const u64 newpol = (pol & ~((1ULL<<a)|(1ULL<<b))) | (u64(c&1)<<a) | (u64(c>>1)<<b);
                const u64 z = pairs.au[p]^newpol;
                uint32_t r = pairs.dir[p]&keep;
                if (qa & ~z) r |= fwd[ea];
                if (qa & z) r |= rev[ea];
                if (qb & ~z) r |= fwd[eb];
                if (qb & z) r |= rev[eb];
                if (!relations.cost(r) && ++losses[c] >= kRejectLoss) options &= ~(1U<<c);
            }
            if (!options) break;
        }
        ++exchange_rows;
        return options;
    };
'''
    if a.enumerate:t=t.replace(needle,helper+needle)
    else:t=t.replace(needle,'    long long exchange_samples = 0;\n'+needle)
    needle='''            mask[eb] ^= (1ULL << a) | (1ULL << b);
        } else {  // window a to another pair'''
    code='''            if (rng.mod(RATE) == 0) {
                COLOR_CHOICE
                pol = (pol & ~((1ULL<<a)|(1ULL<<b))) | (u64(colors&1)<<a) | (u64(colors>>1)<<b);
                ++exchange_samples;
            }
'''.replace('RATE',str(a.exchange))
    if a.enumerate:
        # Here masks have already swapped, so temporarily restore while building the options.
        choice='''const int key = 64*a+b;
                if (selected.size() != unsigned(need)) return false; // handled before masks below
                if (exchange_epoch[key] != epoch) {
                    mask[ea] = olda; mask[eb] = oldb;
                    exchange_options[key] = prepare_exchange(a,b,ea,eb);
                    exchange_epoch[key] = epoch;
                    mask[ea] ^= (1ULL << a) | (1ULL << b);
                    mask[eb] ^= (1ULL << a) | (1ULL << b);
                }
                unsigned options = exchange_options[key];
                if (!options) { mask[ea]=olda; mask[eb]=oldb; return false; }
                int skip = rng.below(__builtin_popcount(options));
                while (skip--) options &= options-1;
                const int colors = __builtin_ctz(options);
                exchange_options[key] &= ~(1U<<colors);'''
        choice=choice.replace('                if (selected.size() != unsigned(need)) return false; // handled before masks below\n','')
        code=code.replace('if (rng.mod(', 'if (selected.size() == unsigned(need) && rng.mod(').replace('COLOR_CHOICE',choice)
    else:code=code.replace('COLOR_CHOICE','const int colors = rng.mod(4);')
    assert needle in t;t=t.replace(needle,needle.replace('        } else {',code+'        } else {'),1)
    t=t.replace('    stats.gobj_after = cur;', '    std::cerr << "exchange_samples = " << exchange_samples << \'\\n\';\n    stats.gobj_after = cur;',1)
    if a.enumerate:t=t.replace('    stats.gobj_after = cur;', '    std::cerr << "exchange_rows = " << exchange_rows << \'\\n\';\n    stats.gobj_after = cur;',1)
if a.transfer_rank:
    # Add a randomized tolerance only to proposal order, retaining the same exact objective.
    old='''                    if (priority < best_priority) { best_priority = priority; shortlist = 0; }
                    if (priority == best_priority) shortlist |= 1U << code;'''
    new='''                    best_priority = std::min(best_priority, priority);
                }
                for (uint32_t q = available; q; q &= q-1) {
                    const int code = __builtin_ctz(q);
                    if (transfer_priority[a][code] <= best_priority + TOL) shortlist |= 1U<<code;'''.replace('TOL',str(a.transfer_rank))
    assert old in t;t=t.replace(old,new,1)
if a.temperature != 1: t=t.replace('const double temp = 0.05 *',f'const double temp = {0.05*a.temperature} *')
if a.restart: t=restart(t,a.restart,a.restart_interval)
if a.guided: t=guided(t,a.guided,a.guide_tolerance,not a.guide_all)
if a.direct_screen: t=direct(t)
if a.unified: t=unified(t)
if a.kind95: t=t.replace('int kind = rng.mod(10),', 'int draw = rng.mod(100), kind=draw<2 ? 0 : draw<5 ? 3 : 8,')
t=t.replace('kWindowRate = 0.6',f'kWindowRate = {a.window_rate}')
if a.sources: t=sources(t,a.sources)
if a.constant_temp>=0: t=t.replace('0.05 * std::pow(0.00125 / 0.05, progress)',str(a.constant_temp))
if a.global_memo: t=globalmemo(t,a.global_memo)
if a.ignore_loss: t=protect(t,a.ignore_loss)
if a.transfer_loss: t=transfer_prior(t,a.transfer_loss)
if a.window_weight: t=window_prior(t,a.window_weight)
if a.batch: t=batch(t,a.batch)
if a.rescue: t=rescue(t,a.rescue)
if a.group:
 t=group(t,a.group)
 i=t.index('    auto prepare_group =');j=t.index('    auto propose =',i)
 t=t[:i]+t[i:j].replace('kRejectLoss',str(a.large_loss))+t[j:]
if a.double:
 t=double(t,a.double)
 i=t.index('    auto prepare_double =');j=t.index('    auto propose =',i)
 t=t[:i]+t[i:j].replace('kRejectLoss',str(a.large_loss))+t[j:]
(h/(a.name+'.cpp')).write_text(s[:l]+t+s[r:])
(h/(a.name+'-README.md')).write_text('改良元: solutions/as6-cap38\n\nassign_windows 内の汎用窓交換で両窓の色を同時に選ぶ。enumerate=trueでは4通りを選定中の71対で事前判定する。\n目的関数、G=38、71対、距離上限26、時間0.50/0.61秒、他の段は維持する。\n設定: '+str(vars(a))+'\n')
f=h/'experiments-config.json';d=json.loads(f.read_text()) if f.exists() else {};d[a.name]=vars(a);f.write_text(json.dumps(d,indent=2)+'\n')
