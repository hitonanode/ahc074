from pathlib import Path

base = Path('solutions/argon-des-perf-stratacut/main.cpp').read_text()


def put(name, code, desc):
    p = Path('solutions/' + name)
    assert not p.exists(), p
    p.mkdir()
    (p / 'main.cpp').write_text(code)
    (p / 'README.md').write_text(
        '改良元: solutions/argon-des-perf-stratacut\n\n' + desc +
        '\n\n探索候補・順序・浮動小数点演算を変えない要求処理の高速化です。Solver のメンバ配置を変えず、'
        '既存スイッチ、ログ、プロファイラ、DesignStore、CLOCK_SCALE をすべて保持します。'
        '新しいスイッチ・stderr 指標はありません。\n')


s = base
s = s.replace('std::array<std::array<u64, K>, 8> cov, disp;',
              'std::array<std::array<u64, K>, 8> cov, wrong;')
s = s.replace('void prepare_post_context(const State& initial)',
              'void prepare_post_context(const State& initial, int u)')
s = s.replace('prepare_post_context(initial);', 'prepare_post_context(initial, u);')
s = s.replace('c.disp[0][j] = paper[k].black;',
              'c.wrong[0][j] = (paper[k].black ^ A[u]) & paper[k].opaque;')
s = s.replace('c.disp[', 'c.wrong[').replace('post_context.disp[', 'post_context.wrong[')
s = s.replace('// A block maps incoming coverage to the first color on its opaque windows. Combining',
              '// A block stores coverage and wrong colors for this request. Combining')
a = s.index('        auto run_of =', s.index('Moves post_optimize('))
b = s.index('                if (cfg.memo) {', a)
part = s[a:b].replace('disp', 'wrong')
part = part.replace('u64 seen = 0, view = 0;', 'u64 seen = 0;')
part = part.replace('cov = paper[k].opaque, wrong = paper[k].black;',
                    'cov = paper[k].opaque;\n                        wrong = post_context.wrong[0][initial_position[k]];')
part = part.replace('if ((wrong ^ A[u]) & cov & ~seen) return false;',
                    'if (wrong & ~seen) return false;')
part = part.replace('                    view |= wrong & ~seen;\n', '')
part = part.replace('if (view != A[u]) return false;',
                    'if (A[u] & ~seen) return false;  // uncovered windows show white')
s = s[:a] + part + s[b:]
put('argon-req-wrongmask', s,
    '後処理の初期積層の区間表に、黒色ではなく現在の要求に対する誤色マスクを保存します。'
    '候補評価では未被覆の誤色があるかを検査し、全体の表示の組み立てを省きます。'
    '未被覆窓が白背景になる条件も維持します。')

s = base
s = s.replace('std::vector<double> best(H + 1, 0);\n        std::vector<int> pick(H + 1, -1);',
              'std::array<double, 65> best{};\n        std::array<int, 65> pick;\n        pick.fill(-1);')
s = s.replace('std::vector<int> local;\n        for (int i = 0; i < M; i++)',
              'std::vector<int> local;\n        local.reserve(M);\n        for (int i = 0; i < M; i++)')
s = s.replace('''        std::vector<int> top;
        column_tops(c, depth + 1, top);
        if (depth < 0 || depth >= int(top.size())) {
            invalid = true;
            return;
        }
        int x = top[depth];''', '''        int x = -1, left = depth;
        if (depth >= 0)
            for (int k : order)
                if (in_column(k, c) && left-- == 0) { x = k; break; }
        if (x < 0) {
            invalid = true;
            return;
        }''')
put('argon-req-planstorage', s,
    '区間 DP の一時配列を上限 64 列の固定配列にし、filler 配置では必要な深さの紙だけを探します。'
    'generic 計画の短い配列は必要量を予約します。候補構築時の小さな動的メモリ確保を減らします。')

s = base
s = s.replace('''        int b = -1;
        for (int i = 0; i < int(order.size()); i++)
            if (order[i] < M) b = i;
        return b;''', '''        int b = -1, found = 0;
        for (int i = 0; i < int(order.size()); i++)
            if (order[i] < M) {
                b = i;
                if (++found == M) break;
            }
        return b;''')
s = s.replace('''            e &= ~paper[x].opaque;
        }
        return false;''', '''            e &= ~paper[x].opaque;
            if (!e) return false;
        }
        return false;''')
s = s.replace('''            covered |= paper[k].opaque;
        }
        return black;''', '''            covered |= paper[k].opaque;
            if (covered == ~u64(0)) break;
        }
        return black;''')
s = s.replace('''        for (int k : order) {
            int c = col_of[k];
            if (c < 0 || !(pending >> handle[c] & 1)''', '''        for (int k : order) {
            if (!pending) break;
            int c = col_of[k];
            if (c < 0 || !(pending >> handle[c] & 1)''')
s = s.replace('''            else if (q == K)
                q = i;''', '''            else if (q == K) {
                q = i;
                if (!lazy) break;  // only the first insertion boundary is needed
            }''')
put('argon-req-earlyscan', s,
    'generic 最下段、可視性、表示、handle の修復費用、即時 filler 配置の走査を、答えが確定した時点で止めます。'
    '遅延配置は従来どおり全列の境界を調べます。')
