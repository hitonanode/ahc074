from pathlib import Path

s = Path('solutions/argon-req-filterbits/main.cpp').read_text()
s = s.replace('std::array<std::array<u64, K>, 8> cov, disp;',
              'struct Block { u64 cov, disp; };\n        std::array<std::array<Block, K>, 8> blocks;')
s = s.replace('''            c.cov[0][j] = paper[k].opaque;
            c.disp[0][j] = paper[k].black;''',
              '''            c.blocks[0][j] = {paper[k].opaque, paper[k].black};''')
s = s.replace('''                c.disp[level][j] = c.disp[level - 1][j] |
                                  (c.disp[level - 1][j + half] & ~c.cov[level - 1][j]);
                c.cov[level][j] = c.cov[level - 1][j] | c.cov[level - 1][j + half];''',
              '''                const auto a = c.blocks[level - 1][j], b = c.blocks[level - 1][j + half];
                c.blocks[level][j] = {a.cov | b.cov, a.disp | (b.disp & ~a.cov)};''')
s = s.replace('''            const u64 left = post_context.cov[level][i];
            cov = left | post_context.cov[level][j];
            disp = post_context.disp[level][i] | (post_context.disp[level][j] & ~left);''',
              '''            const auto a = post_context.blocks[level][i], b = post_context.blocks[level][j];
            cov = a.cov | b.cov;
            disp = a.disp | (b.disp & ~a.cov);''')
s = s.replace('''                    if (breaks[i >> 6] >> (i & 63) & 1) {  // the range is the single paper k
                        cov = paper[k].opaque, disp = paper[k].black;''',
              '''                    if (breaks[i >> 6] >> (i & 63) & 1) {  // the range is the single paper k
                        const auto b = post_context.blocks[0][i];
                        cov = b.cov, disp = b.disp;''')
assert 'post_context.cov' not in s and 'post_context.disp' not in s
p = Path('solutions/argon-req-filterblocks')
assert not p.exists()
p.mkdir()
(p / 'main.cpp').write_text(s)
(p / 'README.md').write_text('改良元: solutions/argon-des-perf-stratacut\n\n'
    '後処理の表示チェックで、区間の被覆と表示色を隣り合う2語の Block にまとめます。'
    '同時に読む値の局所性を上げ、単紙も同じ表から読みます。argon-req-filterbits の'
    '初期位置による区間境界の一括構築と組み合わせます。\n\n'
    '候補・順序・計算結果は不変です。Solver の総サイズと他のメンバの位置は変えません。'
    '予算、全ログ・指標・スイッチ・プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore を保持します。'
    '新規スイッチ・指標はありません。\n')
