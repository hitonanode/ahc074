#!/usr/bin/env python3
"""Variants of a request-side base solver that change one budget each (solutions/legal-alloc-*; this script: solutions/legal-notes).

usage: make_alloc.py [--prefix PREFIX] BASE_DIR NAME [NAME ...]   (or --list; PREFIX default legal-alloc-)
Each variant copies BASE_DIR/main.cpp to solutions/legal-alloc-<NAME>/main.cpp with the replacements
of VARIANTS[NAME] (each old text must occur exactly once) and writes a short README.md. Several
names joined by '+' combine their replacements (legal-alloc-<a>+<b> becomes legal-alloc-<a>-<b>).
"""
import os
import sys

SOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

ENV = 'if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "4";'
ENV2 = 'if(const char* value=std::getenv(local.c_str()))return value;'  # env() settings go right after it


PRESET = {'REPEAT_MIN': '".05"', 'POST_CANDIDATES': '"5"'}  # names search_env already presets


def env(name, value, desc):
    """A fixed default of a search setting (search_env: replaces its preset, or adds one)."""
    if name in PRESET:
        line = f'if(std::strcmp(name,"{name}")==0)return {PRESET[name]};'
        return ([(line, f'if(std::strcmp(name,"{name}")==0)return "{value}";')], desc)
    return ([(ENV2, ENV2 + f'\n        if(std::strcmp(name,"{name}")==0)return "{value}";')], desc)


def width(value):
    return ([(ENV, f'if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "{value}";')],
            f'中立の書き換えの候補の数 NEUTRAL_WIDTH を 4 から {value} にする')


def const(old, new, desc):
    return ([(old, new)], desc)


POST = 'static constexpr int kPostCandidates = 3;'
PICKS = 'if (picks.size() > 6) picks.resize(6);'
PAIRS = 'if (pair_picks.size() > 6) pair_picks.resize(6);'
PAIR12 = 'if (pairs.size() > 12) pairs.resize(12);'
EJECT = 'chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);'
BEAM = '        if (best_normal < 1e17) {\n            start_plan(st0);\n            beam_enabled = true;'
WEIGHTED = 'if (weighted_ready) if (const auto* cached = find_cached_plan(weighted_raw);'
RM = 'for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)'
FMS = 'const std::vector<int> fms = any_out ? std::vector<int>{1, 4} : std::vector<int>{1};'
TIE = 'chosen_path = tie_choice(st0, u, std::move(chosen_path) OP_TAG(, op_tags));'
MERGE = '        merge_double_moves(st0, chosen_path OP_TAG(, op_tags));\n        return chosen_path;'
HELPERS = 'if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {\n            bool used = false;'
ALTS = '        if (future_candidates.size() > 1) {\n            auto chosen = save();'

ANCHORS = ('            for (int i = int(edits.size()) - 1; !delete_only && i >= 0; i--) {\n'
           '                const int k = edits[i].paper;\n                if (!initial_extra[k]) {\n')
REWRITE = ('            for (int i = int(edits.size()) - 1; !delete_only && i >= 0; i--) {\n'
           '                const int k = edits[i].paper;\n                if (!initial_extra[k]) continue;\n')

EXTRA = '        for (const auto& f : initial.fillers) initial_extra[f.paper] = true;\n'
END_FILLER = ('        std::array<bool, K> end_filler{};  // the fillers of the plan (the state at the call)\n'
              '        for (const auto& f : fillers) end_filler[f.paper] = true;\n')

VARIANTS = {
    # reductions
    'ns1': env('NS_ROUNDS', 1, '中立の書き換えの回数 NS_ROUNDS を 2 から 1 にする'),
    'ns0': env('NS_ROUNDS', 0, '中立の書き換えをしない（NS_ROUNDS = 0）'),
    'nw3': width(3),
    'nw2': width(2),
    'nd1': env('NEUTRAL_DEPTH', 1, '中立の書き換えの候補を編集し直さない（NEUTRAL_DEPTH = 1）'),
    'pc2': const(POST, 'static constexpr int kPostCandidates = 2;', '編集する計画の数 kPostCandidates を 3 から 2 にする'),
    'pc1': const(POST, 'static constexpr int kPostCandidates = 1;', '編集する計画を最良の 1 つだけにする（kPostCandidates = 1）'),
    'exp3': env('POST_CANDIDATES', 3, '追加の候補の集め方 POST_CANDIDATES を 5 から 3 にする（追加の候補がなくなる）'),
    'exp4': env('POST_CANDIDATES', 4, '追加の候補の集め方 POST_CANDIDATES を 5 から 4 にする'),
    'nobeam': const(BEAM, BEAM.replace('if (best_normal < 1e17)', 'if (false && best_normal < 1e17)'),
                    '鎖の探索つきの計画（beam）を作らない'),
    'noweighted': const(WEIGHTED, WEIGHTED.replace('if (weighted_ready)', 'if (false && weighted_ready)'),
                        '重みつきの計画の仕上げ（finish_weighted_plan）をしない'),
    'nohelpers': const(HELPERS, HELPERS.replace('if (interleave &&', 'if (false && interleave &&'), '補助紙の計画を作らない'),
    'h3': ([(PICKS, 'if (picks.size() > 3) picks.resize(3);'), (PAIRS, 'if (pair_picks.size() > 3) pair_picks.resize(3);')],
           '補助紙の計画の候補を 1 枚・2 枚とも 6 から 3 にする'),
    'h4': ([(PICKS, 'if (picks.size() > 4) picks.resize(4);'), (PAIRS, 'if (pair_picks.size() > 4) pair_picks.resize(4);')],
           '補助紙の計画の候補を 1 枚・2 枚とも 6 から 4 にする'),
    'nopairs': const(PAIRS, 'if (pair_picks.size() > 0) pair_picks.resize(0);', '2 枚の補助紙の計画を作らない'),
    'pair6': const(PAIR12, 'if (pairs.size() > 6) pairs.resize(6);', '2 枚の補助紙の組の候補を 12 から 6 にする'),
    'ej2': const(EJECT, EJECT.replace(', 4, true)', ', 2, true)'), '最良の計画の取り出しの回数を 4 から 2 にする'),
    'ej1': const(EJECT, EJECT.replace(', 4, true)', ', 1, true)'), '最良の計画の取り出しの回数を 4 から 1 にする'),
    'rm2': const(RM, 'for (int rm = 1; rm <= 2; rm++)', '計画の候補から ret_mode 3 を除く'),
    'fm1': const(FMS, 'const std::vector<int> fms = std::vector<int>{1};', '計画の候補から fret_mode 4 を除く'),
    'notie': const(TIE, '', '比べ直し（tie_choice）をしない（時間の確認用）'),
    'nomerge': const(MERGE, '        return chosen_path;', '2 回動かす紙の統合をしない（時間の確認用）'),
    'noalts': const(ALTS, ALTS.replace('if (future_candidates.size() > 1)', 'if (false && future_candidates.size() > 1)'),
                    '次点の計画の編集をしない（追加の候補の段には残る）'),
    'norewrite': const(REWRITE, REWRITE.replace('!delete_only && i >= 0', 'false && i >= 0'),
                       '後処理の「削除と付け替えの組」（古い補助紙の差し込み先を変え、別の手を 1 つ消す）をしない'),
    'noanchors': const(ANCHORS, ANCHORS.replace('!delete_only && i >= 0', 'false && i >= 0'),
                       '後処理の「差し込み先の付け替え」（古い補助紙・2 回動かす紙）をしない'),
    'pdel': env('NS_DELETE_ONLY', 1, '中立の書き換えの候補の編集を、削除だけにする（NS_DELETE_ONLY = 1。付け替えと組をしない）'),
    'ej0': const(EJECT, EJECT.replace(', 4, true)', ', 0, true)'), '最良の計画の取り出し（eject_main）をしない'),
    'ancx': const(ANCHORS + '                    int repeats = 0;\n                    for (const auto& e : edits) repeats += e.paper == k;\n                    if (repeats < 2) continue;\n',
                  ANCHORS + '                    continue;\n',
                  '後処理の「差し込み先の付け替え」を古い補助紙だけにする（2 回動かす紙はしない）'),
    'ancr': const(ANCHORS, ANCHORS.replace('                if (!initial_extra[k]) {\n', '                if (true) {\n'),
                  '後処理の「差し込み先の付け替え」を 2 回動かす紙だけにする（古い補助紙も 2 回動かすときだけ）'),
    'pl0': env('PLAN_LIMIT', 0, '追加の候補を本探索しない（PLAN_LIMIT = 0。軽い選別だけ）'),
    'pej1': env('PLAN_EJECTS', 1, '追加の候補の取り出しの回数 PLAN_EJECTS を 2 から 1 にする'),
    'nw1': width(1),
    'two0': env('NS_TWO', 0, '中立の書き換えの候補集めで 2 対 2 の書き換えをしない（NS_TWO = 0）'),
    'one0': env('NS_ONE', 0, '中立の書き換えの候補集めで 1 対 1 の書き換えをしない（NS_ONE = 0）'),
    'oa1': env('ONE_ANCHORS', 1, '1 対 1 の書き換えの差し込み先の数 ONE_ANCHORS を 2 から 1 にする'),
    'slack15': env('NEUTRAL_SLACK', '.15', '中立の書き換えの候補に入れる値の幅 NEUTRAL_SLACK を 0.25 から 0.15 にする'),
    'prom25': env('PROMISING_SLACK', '.25', '短い候補・2 回動かす紙のある候補の値の幅 PROMISING_SLACK を 0.75 から 0.25 にする'),
    'pick3': const(PICKS, 'if (picks.size() > 3) picks.resize(3);', '1 枚の補助紙の計画の候補を 6 から 3 にする'),
    'pp3': const(PAIRS, 'if (pair_picks.size() > 3) pair_picks.resize(3);', '2 枚の補助紙の計画の候補を 6 から 3 にする'),
    'h2': ([(PICKS, 'if (picks.size() > 2) picks.resize(2);'), (PAIRS, 'if (pair_picks.size() > 2) pair_picks.resize(2);')],
           '補助紙の計画の候補を 1 枚・2 枚とも 6 から 2 にする'),
    # expansions
    'pd4': ([('if (k != d && c != col_of[d] && depths[k] <= 3) available.push_back(k);',
              'if (k != d && c != col_of[d] && depths[k] <= 4) available.push_back(k);'),
             ('if (depths[x] < 0 || depths[x] > 3) continue;', 'if (depths[x] < 0 || depths[x] > 4) continue;')],
            '2 枚の補助紙の計画で、2 枚とも深さ 3 までを 4 までにする'),
    'oa3': env('ONE_ANCHORS', 3, '1 対 1 の書き換えの差し込み先の数 ONE_ANCHORS を 2 から 3 にする'),
    'tri1': env('NS_TRIPLES', 1, '中立の書き換えの候補集めで 3 対 2 の書き換えもする（NS_TRIPLES = 1）'),
    'pp8': const(PAIRS, 'if (pair_picks.size() > 8) pair_picks.resize(8);', '2 枚の補助紙の計画の候補を 6 から 8 にする'),
    'pick8': const(PICKS, 'if (picks.size() > 8) picks.resize(8);', '1 枚の補助紙の計画の候補を 6 から 8 にする'),
    'anc2x': ([('            // Other anchors for an old extra / a paper moved twice.\n'
                '            for (int i = int(edits.size()) - 1; !delete_only && i >= 0; i--) {\n',
                '            // Other anchors for an old extra / a paper moved twice (legal-alloc-anc2x: a second sweep\n'
                '            // when the first one changed the plan).\n'
                '            for (int sweep = 0, changed = 1; sweep < 2 && changed; sweep++) {\n'
                '            changed = 0;\n'
                '            for (int i = int(edits.size()) - 1; !delete_only && i >= 0; i--) {\n'),
               ('                    if (evaluate(trial)) chosen = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));\n'
                '                }\n                edits = std::move(chosen);\n                i = std::min(i, int(edits.size()));\n            }\n',
                '                    if (evaluate(trial)) chosen = anchorize(initial_bytes, best_ops OP_TAG(, best_tags)), changed = 1;\n'
                '                }\n                edits = std::move(chosen);\n                i = std::min(i, int(edits.size()));\n            }\n            }\n')],
              '後処理の「差し込み先の付け替え」で計画が変わったら、もう 1 回付け替えを通す'),
    'ancf': ([(EXTRA, EXTRA + END_FILLER),
              (ANCHORS, ANCHORS.replace('if (!initial_extra[k]) {', 'if (!initial_extra[k] && !end_filler[k]) {'))],
             '後処理の「差し込み先の付け替え」を、計画の後に補助紙（列の外）になる紙にもする'),
    'ancall': const(ANCHORS, ANCHORS.replace('if (!initial_extra[k]) {', 'if (false) {'),
                    '後処理の「差し込み先の付け替え」を、計画のすべての手の紙にする'),
    'rwf': ([(EXTRA, EXTRA + END_FILLER),
             (REWRITE, REWRITE.replace('if (!initial_extra[k]) continue;', 'if (!initial_extra[k] && !end_filler[k]) continue;'))],
            '後処理の「削除と付け替えの組」を、計画の後に補助紙になる紙にもする'),
    'pc4': const(POST, 'static constexpr int kPostCandidates = 4;', '編集する計画の数 kPostCandidates を 3 から 4 にする'),
    'pc5': const(POST, 'static constexpr int kPostCandidates = 5;', '編集する計画の数 kPostCandidates を 3 から 5 にする'),
    'nw5': width(5),
    'nw6': width(6),
    'ns3': env('NS_ROUNDS', 3, '中立の書き換えの回数 NS_ROUNDS を 2 から 3 にする'),
    'rmin0': env('REPEAT_MIN', 0, '中立の書き換えの 2 回目以降を、改善が 0.05 未満でも行う（REPEAT_MIN = 0）'),
    'exp6': env('POST_CANDIDATES', 6, '追加の候補の集め方 POST_CANDIDATES を 5 から 6 にする'),
    'exp8': env('POST_CANDIDATES', 8, '追加の候補の集め方 POST_CANDIDATES を 5 から 8 にする'),
    'pl2': env('PLAN_LIMIT', 2, '追加の候補の本探索の数 PLAN_LIMIT を 1 から 2 にする'),
    'pej3': env('PLAN_EJECTS', 3, '追加の候補の取り出しの回数 PLAN_EJECTS を 2 から 3 にする'),
    'pej4': env('PLAN_EJECTS', 4, '追加の候補の取り出しの回数 PLAN_EJECTS を 2 から 4 にする'),
    'refine1': env('REFINE_BEST', 1, '中立の書き換えで良くなった計画を、もう 1 回編集と取り出しにかける（REFINE_BEST = 1）'),
    'short1': env('NS_SHORT_ROUNDS', 1, '中立の書き換えの候補ごとに、取り出しと編集を 1 回足す（NS_SHORT_ROUNDS = 1）'),
    'alt1': env('NS_ALTERNATE', 1, '編集した次点の計画にも取り出しをかける（NS_ALTERNATE = 1）'),
    'slack35': env('NEUTRAL_SLACK', '.35', '中立の書き換えの候補に入れる値の幅 NEUTRAL_SLACK を 0.25 から 0.35 にする'),
    'ej6': const(EJECT, EJECT.replace(', 4, true)', ', 6, true)'), '最良の計画の取り出しの回数を 4 から 6 にする'),
    'h8': ([(PICKS, 'if (picks.size() > 8) picks.resize(8);'), (PAIRS, 'if (pair_picks.size() > 8) pair_picks.resize(8);')],
           '補助紙の計画の候補を 1 枚・2 枚とも 6 から 8 にする'),
    'pair18': const(PAIR12, 'if (pairs.size() > 18) pairs.resize(18);', '2 枚の補助紙の組の候補を 12 から 18 にする'),
    'pl2s': ([(ENV2, ENV2 + '\n        if(std::strcmp(name,"PLAN_LIMIT")==0)return "2";\n        if(std::strcmp(name,"PLAN_SHORTLIST")==0)return "0";')],
             '追加の候補を長さで絞らず（PLAN_SHORTLIST = 0）、本探索を 2 つにする（PLAN_LIMIT = 2）'),
    'sl0': env('PLAN_SHORTLIST', 0, '追加の候補を長さで絞らない（PLAN_SHORTLIST = 0）'),
}


def main():
    if sys.argv[1:] == ['--list']:
        for k, (_, d) in VARIANTS.items():
            print(f'{k:12s} {d}')
        return
    args = sys.argv[1:]
    prefix = 'legal-alloc-'
    if args[0] == '--prefix':
        prefix, args = args[1], args[2:]
    base = os.path.abspath(args[0])
    src = open(os.path.join(base, 'main.cpp')).read()
    base_name = os.path.basename(base.rstrip('/'))
    for name in args[1:]:
        parts = name.split('+')
        s = src
        descs = []
        for part in parts:
            reps, desc = VARIANTS[part]
            for old, new in reps:
                n = s.count(old)
                assert n == 1, (part, old[:60], n)
                s = s.replace(old, new)
            descs.append(desc)
        out = os.path.join(SOL, prefix + '-'.join(parts))
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, 'main.cpp'), 'w').write(s)
        with open(os.path.join(out, 'README.md'), 'w') as f:
            f.write(f'# {prefix}{"-".join(parts)}（注文処理の予算を変える版）\n\n'
                    f'改良元: `solutions/{base_name}`。`solutions/legal-notes/make_alloc.py` で作った。\n\n'
                    '## 改良元からの差分\n\n')
            for d in descs:
                f.write(f'- {d}。\n')
            f.write('\n注文処理の各部分の、時間あたりの価値を測るための版（設計は変えない）。指標は改良元と同じ。\n')
        print(out)


if __name__ == '__main__':
    main()
