from pathlib import Path
base = Path('solutions/argon-des-perf-stratacut/main.cpp').read_text()


def put(name, code, desc):
    p = Path('solutions/' + name)
    assert not p.exists(), p
    p.mkdir()
    (p / 'main.cpp').write_text(code)
    (p / 'README.md').write_text('改良元: solutions/argon-des-perf-stratacut\n\n' + desc +
        '\n\n出力不変の要求処理高速化。候補順、計算結果、キャッシュのアクセス、既存スイッチ、ログ、'
        '全プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore を保持します。新規スイッチ・指標はありません。\n')


def key_change(s):
    old = '''        std::array<bool, K> extra{};  // the lifted paper and the fillers (out of their columns)
        if (top_d >= 0) extra[top_d] = true;'''
    new = '''        std::array<bool, K> extra;  // every paper excluded from the in-column subsequence
        for (int k = 0; k < K; ++k) extra[k] = col_of[k] < 0;
        if (top_d >= 0) extra[top_d] = true;'''
    assert s.count(old) == 1
    s = s.replace(old, new)
    s = s.replace('for (int k : order) if (col_of[k] >= 0 && !extra[k]) key[key_size++] = k;',
                  'for (int k : order) { key[key_size] = k; key_size += !extra[k]; }')
    return s


def filter_change(s):
    a = s.index('                // moved: the papers of the edits;')
    b = s.index('                auto next_break =', a)
    old = s[a:b]
    new = '''                // Bit positions refer to the initial order. A run ends at a moved paper,
                // immediately above one, or at an anchor. Build all predecessors in three shifts.
                for (const Edit& e : trial) {
                    const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;
                    if (a == k) return false;
                    const int p = initial_position[k];
                    moved[p >> 6] |= 1ULL << (p & 63);
                    if (e.anchor >= 0) {
                        const int q = initial_position[e.anchor];
                        breaks[q >> 6] |= 1ULL << (q & 63);
                    }
                    splice_after(next, prev, k, a);
                }
                for (int w = 0; w < 3; ++w) {
                    breaks[w] |= moved[w] | (moved[w] >> 1);
                    if (w < 2) breaks[w] |= moved[w + 1] << 63;
                }
'''
    s = s[:a] + new + s[b:]
    s = s.replace('''                    u64 cov, disp;
                    if (moved[k >> 6] >> (k & 63) & 1) {''', '''                    u64 cov, disp;
                    const int i = initial_position[k];
                    if (breaks[i >> 6] >> (i & 63) & 1) {''')
    s = s.replace('const int i = initial_position[k], e = next_break(i);',
                  'const int e = next_break(i);')
    return s


put('argon-req-valuekey', key_change(base),
    '次状態価値の完全一致キーを作る際、列に属さない紙と列外の紙を一つの除外表にまとめます。'
    '列内の紙列を分岐なしで詰めます。キーのバイト列・ハッシュ・アクセス回数は従来と同じです。')
put('argon-req-filterbits', filter_change(base),
    '最終表示チェックの区間境界を、初期位置で表した移動紙集合から一括計算します。'
    '直前の位置は3語のシフトで求め、各編集での設定を省きます。長さ1の区間は紙を直接参照します。')
put('argon-req-keybits', filter_change(key_change(base)),
    'argon-req-valuekey のキー構築と argon-req-filterbits の区間境界計算を組み合わせます。')
