"""Comparatorのラベル対称性で距離表の全始点BFSを置き換える。"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
s = (root / 'solutions/argon-des-perf-stratacut/main.cpp').read_text()
old = '''        for (int a = 0; a < n; a++) {
            uint8_t* da = &dist[a * n];
            int qb = 0, qe = 0;
            q[qe++] = a;
            da[a] = 0;
            while (qb < qe) {
                const int x = q[qb++];
                for (int y : next[x])
                    if (y >= 0 && da[y] == 255) da[y] = da[x] + 1, q[qe++] = y;
            }
        }
'''
new = '''        // Renaming sheets preserves every legal move, including the immovable bottom
        // position. One BFS gives the identity row; all other rows are relabelings.
        int qb = 0, qe = 0;
        q[qe++] = 0;
        dist[0] = 0;
        while (qb < qe) {
            const int x = q[qb++];
            for (int y : next[x])
                if (y >= 0 && dist[y] == 255) dist[y] = dist[x] + 1, q[qe++] = y;
        }
        std::vector<std::vector<int>> renamed(M * M);
        for (int i = 0; i < M; ++i) for (int j = i + 1; j < M; ++j) {
            auto& index = renamed[i * M + j];
            index.resize(n);
            for (int b = 0; b < n; ++b) {
                auto r = perms[b];
                for (int& x : r) {
                    if (x == i) x = j;
                    else if (x == j) x = i;
                }
                index[b] = order_index(r);
            }
        }
        for (int a = 1; a < n; ++a) {
            int i = 0;
            while (perms[a][i] == i) ++i;
            // Earlier positions are fixed, so j > i. This swap makes the source
            // lexicographically smaller, and its distance row is already complete.
            const int j = perms[a][i];
            const auto& index = renamed[i * M + j];
            const int parent = index[a];
            assert(parent < a);
            for (int b = 0; b < n; ++b) dist[a * n + b] = dist[parent * n + index[b]];
        }
'''
assert s.count(old) == 1
s = s.replace(old, new).replace('// BFS from every order', '// BFS and label symmetry')
dest = root / 'solutions/argon-des-comparator-orbit'
dest.mkdir()
(dest / 'main.cpp').write_text(s)
(dest / 'README.md').write_text('''改良元: solutions/argon-des-perf-stratacut

Comparator::build_tablesの距離表を、全始点BFSから1回のBFSと紙番号の置換で作る。
操作は紙の位置だけで定まり、紙番号を一括して付け替えても合法な遷移と距離は変わらない。
恒等順序からの距離だけをBFSで求め、他の始点は先頭の非固定位置を直す交換で
辞書順の小さい始点に帰着させる。距離表の各行・各列の番号と値は元と同じ。
perms・next・below、経路の同点処理、設計・注文の候補・乱数・反復予算は維持する。

新しいスイッチ・指標はない。af_comparator_tables_secがこの処理の既存の計測値。
全ログ・@paper/@ops・profiler・予算スイッチ、CLOCK_SCALE・LOCAL_BENCH・DesignStore、
段の目印と目次を保持する。変更はGeneric layerのComparator::build_tablesだけ。
''')
verify = root / 'solutions/argon-des-comparator-orbit-verify'
verify.mkdir()
check = '''        // Measurement build: independently rebuild every row by the original BFS.
        std::vector<uint8_t> reference(n);
        for (int a = 0; a < n; ++a) {
            std::fill(reference.begin(), reference.end(), 255);
            int begin = 0, end = 0;
            q[end++] = a;
            reference[a] = 0;
            while (begin < end) {
                const int x = q[begin++];
                for (int y : next[x])
                    if (y >= 0 && reference[y] == 255)
                        reference[y] = reference[x] + 1, q[end++] = y;
            }
            for (int b = 0; b < n; ++b) assert(dist[a * n + b] == reference[b]);
        }
        std::cerr << "argon_distance_verified = " << n * n << '\\n';
'''
(verify / 'main.cpp').write_text(s.replace(new, new+check))
(verify / 'README.md').write_text('''改良元: solutions/argon-des-perf-stratacut

距離表を紙番号の置換で作るargon-des-comparator-orbitの検査版。
元の全始点BFSも独立に実行し、距離表の全要素が一致することをassertで確かめる。
argon_distance_verifiedは照合した要素数。検査後も通常の設計・注文処理を行う。
この余分な検査の時間は高速化の比較には使わない。全ログ・profiler・スイッチを維持する。
''')
print(dest, verify)
