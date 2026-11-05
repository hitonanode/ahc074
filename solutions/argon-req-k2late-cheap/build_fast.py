from pathlib import Path
p=Path('solutions/argon-req-k2late-fast'); assert not p.exists(); p.mkdir()
s=Path('solutions/argon-req-k2late-cheap/main.cpp').read_text()
a=s.index('        struct Choice {',s.index('    void joint_alternatives('))
b=s.index('    void run_joint(',a)
s=s[:a]+'''        struct Choice { double gain = 0; std::array<u64, 3> papers{}; int node = -1; };
        struct Node { Cand interval; int previous; };
        static std::vector<Node> nodes;
        nodes.clear();
        std::array<std::array<Choice, 2>, 65> best;
        std::array<int, 65> count{};
        count[0] = 1;
        for (int c = 0; c < H; ++c) {
            auto& list = best[c + 1];
            int& n = count[c + 1];
            list = best[c]; n = count[c];
            for (const auto& cd : candidates[c]) for (int j=0; j<count[cd.lvl]; ++j) {
                Choice q = best[cd.lvl][j];
                const int previous = q.node;
                const int paper = paper_id(cd);
                q.papers[paper >> 6] |= u64(1) << (paper & 63);
                q.gain += cd.gain;
                int slot = 0;
                while (slot < n && list[slot].papers != q.papers) ++slot;
                if (slot < n) {
                    if (q.gain <= list[slot].gain + 1e-9) continue;
                } else if (n == 2) {
                    if (q.gain <= list[1].gain) continue;
                    slot = 1;
                } else ++n;
                q.node = nodes.size();
                nodes.push_back({cd, previous});
                list[slot] = q;
                // Stable order: on an equal gain the earlier candidate remains first.
                if (n == 2 && list[1].gain > list[0].gain) std::swap(list[0], list[1]);
            }
        }
        std::array<u64, 3> primary_papers{};
        for (const auto& cd : primary) {
            const int paper = paper_id(cd);
            primary_papers[paper >> 6] |= u64(1) << (paper & 63);
        }
        joint_choices = {primary};
        for (int i=0; i<count[H] && joint_choices.size()<2; ++i) {
            const auto& q = best[H][i];
            if (q.papers == primary_papers) continue;
            std::vector<Cand> picks;
            for (int node=q.node; node>=0; node=nodes[node].previous) picks.push_back(nodes[node].interval);
            joint_choices.push_back(std::move(picks));
        }
    }
'''+s[b:]
(p/'main.cpp').write_text(s)
(p/'README.md').write_text(Path('solutions/argon-req-k2late-cheap/README.md').read_text()+'''
第2解の区間DPは各位置に2状態だけを保持し、候補ごとの選択列コピーとstable_sortを、固定長2要素と前駆ノードによる復元へ置き換えた。同じ紙集合の統合、浮動小数点加算順、同点で先の候補を保つ順序は元の第2解版と一致する。追加のスイッチ・指標はない。
''')
print(p)
