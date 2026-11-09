"""dual30 から担当 A の小変更を独立に作る。既存の解法には書かない。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = (ROOT / 'solutions/dcomp-combo-dual30/main.cpp').read_text()

def replace(s, old, new, count=1):
    assert s.count(old) == count, (old, s.count(old), count)
    return s.replace(old, new)

def reset(s, value=4.0):
    return replace(s, '    static constexpr double reset_strength = 2.0;', f'''#ifdef LOCAL_BENCH
    inline static const double reset_strength = env_real("D30A_RESET", {value});
#else
    static constexpr double reset_strength = {value};
#endif''')

def fret(s, value=0.7):
    s = replace(s, '    inline static double kClimbProxyWeight = 0.5;', f'''    inline static double kClimbProxyWeight = 0.5;
#ifdef LOCAL_BENCH
    inline static const double kFillerReturn = env_real("D30A_FRET", {value});
#else
    static constexpr double kFillerReturn = {value};
#endif''')
    s = replace(s, '0.6 * (1 - p0 - p1)', 'kFillerReturn * (1 - p0 - p1)')
    return replace(s, 'and 0.6 more if there are two', 'and kFillerReturn more if there are two')

def gc(s, value=0.9):
    s = replace(s, 'double env_real(const char* name,double fallback);', f'''double env_real(const char* name,double fallback);
// Realized generic moves after helpers/repairs, used only by the design model.
#ifdef LOCAL_BENCH
const double kGenericRealized = std::clamp(env_real("D30A_GC", {value}), 0.5, 1.5);
#else
constexpr double kGenericRealized = {value};
#endif''')
    s = replace(s, 'gcost[u.a][u.b] * 2;', 'gcost[u.a][u.b] * 2 * kGenericRealized;')
    s = replace(s, '2 * gcost[a][b]', '2 * kGenericRealized * gcost[a][b]', 2)
    s = replace(s, '2 * d.gcost[a][b]', '2 * kGenericRealized * d.gcost[a][b]')
    s = replace(s, '    std::vector<int> full144(np);  // 144 differences of each pair', '''    // Keep the exact generic key and rescale other terms, preserving the 17-bit key.
    // At 0.9 this gives (2000 * hd + 5 * both_of + 160 * differences).
    const int handle_key = int(std::lround(1800 / kGenericRealized));
    const int difference_key = int(std::lround(144 / kGenericRealized));
    std::vector<int> full144(np);  // rescaled differences of each pair''')
    s = replace(s, 'full144[p] = 144 *', 'full144[p] = difference_key *')
    s = replace(s, 'const int key = 1800 *', 'const int key = handle_key *', 2)
    s = replace(s, '(need - matched) * 10.0;', '(need - matched) * (10.0 / kGenericRealized);', 2)
    s = replace(s, '// hd <= 26, full144 <= 144*26, rel <= 4380: the key fits 17 bits.',
                '// hd <= 26, scale >= 0.5, rel <= 4380: the key fits 17 bits.', 2)
    return s

def seg(s):
    s = replace(s, '    static constexpr int kAnnealSegments = 4;', '''#ifdef LOCAL_BENCH
    inline static const int kAnnealSegments = env_int("D30A_SEGMENTS") == 4 ? 4 : 8;
#else
    static constexpr int kAnnealSegments = 8;
#endif''')
    s = replace(s, 'int endSegment = 4)', 'int endSegment = kAnnealSegments)')
    s = replace(s, '            const int fi = fixedIterations ? fixedIterations / kAnnealSegments : 0;', '''            // The old loop checks every 256 proposals. Split its actual work into
            // 256-step blocks, so eight restores do not increase the work budget.
            const int blocks = fixedIterations ? 4 * ((fixedIterations / 4 + 255) / 256) : 0;
            const int fi = !fixedIterations ? 0 : kAnnealSegments == 4 ? fixedIterations / 4
                : 256 * (((s + 1) * blocks) / kAnnealSegments - (s * blocks) / kAnnealSegments);''')
    s = replace(s, '    const int shared=2;', '    const int shared=Design::kAnnealSegments/2;')
    s = replace(s, 'des->reheat_start=shared/4.;', 'des->reheat_start=double(shared)/Design::kAnnealSegments;')
    return replace(s, 'int(anneal_iters*branch_scale),shared,4)',
                   'int(anneal_iters*branch_scale),shared,Design::kAnnealSegments)')

DESCRIPTIONS = {
    'reset4': '焼きなましのハンドル穴費用の reset_strength を 2.0 から 4.0 にする。列の需要で頭色が戻る効果を強め、少数色の穴を減らす配置を狙う。refresh_reset が作る値を参照する再割り当ても同じ値を使う。V、filler_climb の明示的な 2.0、再割り当ての strength 引数は変えない。\n\nLOCAL_BENCH の D30A_RESET で値を指定でき、2 で元に戻る。',
    'fret07': '仕上げの covered_gain における穴埋め紙の返却費用を 0.6 から 0.7 にする。配置 1 手の費用は保ち、返却が必要な確率に掛ける係数だけを注文処理に近づける。この関数を共用する filler_climb、ProbabilityHead、穴あけに同じ変更が効く。\n\nLOCAL_BENCH の D30A_FRET で係数を指定でき、0.6 で元に戻る。',
    'gc09': '設計が見積もる汎用層の操作費用を 0.9 倍する。初期化・焼きなまし・再割り当てに揃えて適用する。窓割り当てでは整数キーを保つため、汎用項は 5 のまま、ハンドル差の係数を 1800→2000、全窓差を 144→160、未対応対の罰を 10/9 倍にする。Clang と GCC の両経路を同じ式にする。V の GenericTable は変更しない。\n\nLOCAL_BENCH の D30A_GC で実現率を指定でき、1 で元に戻る。範囲は整数キーの安全性のため 0.5〜1.5。窓の係数は整数に四捨五入する。',
    'seg8': '設計の焼きなましを 4 分割から 8 分割にする。各区間の最良状態への復帰と reset 需要の更新を倍の頻度で行う。共有区間は前半の 4 区間、4 分岐は後半の 4 区間、再加熱開始は全体の 0.5 のまま。元の 256 回ごとの停止検査で実際に行う反復数を 256 回単位で分配するため、総反復数は元と等しい。\n\nLOCAL_BENCH の D30A_SEGMENTS=4 で元の分割・反復数に戻る。既定は 8。',
}

def write(name, source, description):
    out = ROOT / 'solutions' / ('d30a-' + name)
    out.mkdir(exist_ok=False)
    (out/'main.cpp').write_text(source)
    (out/'README.md').write_text('改良元: solutions/dcomp-combo-dual30\n\n' + description +
        '\n\n固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。新しい stderr 指標はない。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。\n')

if __name__ == '__main__':
    for name, fn in [('reset4', reset), ('fret07', fret), ('gc09', gc), ('seg8', seg)]:
        write(name, fn(BASE), DESCRIPTIONS[name])
