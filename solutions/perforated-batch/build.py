from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/perforated-screen/perforate.hpp').read_text()
s=s.replace('    static inline int overlap_samples=16;','    static inline int overlap_samples=16;\n    static inline int group_size=1,extra_trials=4000;')
s=s.replace('std::vector<std::pair<int,int>> candidates;','std::vector<std::pair<int,u64>> candidates;')
s=s.replace('candidates.push_back({k,__builtin_ctzll(bits)});','if(group_size==1)candidates.push_back({k,1ULL<<__builtin_ctzll(bits)});')
s=s.replace('            std::shuffle(candidates.begin(),candidates.end(),rng);','''            if(group_size>1)for(int it=0;it<extra_trials;it++){
                int k=7+rng()%(K-7),c=columns[k];u64 possible=allowed[k]&low_bits(c);
                if(__builtin_popcountll(possible)<group_size)continue;
                u64 mask=0;for(int j=0;j<group_size;j++){
                    int rank=rng()%__builtin_popcountll(possible);u64 z=possible;while(rank--)z&=z-1;u64 bit=z&-z;mask|=bit;possible^=bit;
                }
                candidates.push_back({k,mask});
            }
            std::shuffle(candidates.begin(),candidates.end(),rng);''')
s=s.replace('for(auto[k,c]:candidates){\n                trials++;const u64 bit=1ULL<<c;bool remove=opacity[k]&bit;', 'for(auto[k,bit]:candidates){\n                trials++;u64 removed=opacity[k]&bit;')
s=s.replace('''                double old_cost=cost(c),old_separate=separate_profit();opacity[k]^=bit;
                for(int u:owners[k])counts[c][target[u]>>c&1]+=remove?1:-1;
                const double delta=cost(c)-old_cost;''','''                double delta=0,old_separate=separate_profit();
                for(u64 bits=bit;bits;bits&=bits-1){int c=__builtin_ctzll(bits);delta-=cost(c);for(int u:owners[k])counts[c][target[u]>>c&1]+=(removed>>c&1)?1:-1;delta+=cost(c);}
                opacity[k]^=bit;''')
s=s.replace('opacity[k]^=bit;for(int u:owners[k])counts[c][target[u]>>c&1]+=remove?-1:1;', 'opacity[k]^=bit;for(u64 bits=bit;bits;bits&=bits-1){int c=__builtin_ctzll(bits);for(int u:owners[k])counts[c][target[u]>>c&1]+=(removed>>c&1)?-1:1;}')
assert 'bool remove'not in s and'old_cost=cost(c)'not in s
(p/'perforate.hpp').write_text(s)
s=Path('solutions/perforated-screen/probe.cpp').read_text().replace('setting<4','setting<6')
s=s.replace('Perforation::screen_weight=setting==1?0:setting==2?1:2;', 'Perforation::screen_weight=1;Perforation::group_size=setting<=1?1:setting<=3?2:3;')
s=s.replace('if(setting)design.run(.5,1,false);','if(setting){double weight=setting==3||setting==5?.35:.5;design.run(weight,1,false);if(setting>=2){Perforation::group_size=1;design.run(weight,1,false);}}')
(p/'probe.cpp').write_text(s)
r=Path('solutions/perforated-screen/run.py').read_text().replace('ahc074-perforated-screen','ahc074-perforated-batch').replace('20261103-220920_post-prune','20261103-230624_post-repair').replace('range(1,4)','range(1,6)');(p/'run.py').write_text(r)
(p/'README.md').write_text('''# 複数のハンドルの穴をまとめて変更する

改良元: solutions/perforated-screen。注文処理は新しい基準 solutions/post-repair に合わせる。

商品紙の自分の取り出し窓より浅い印刷について、1個の穴追加では利益が出なくても、2〜3個を同時に開けると多くの商品を補助できる可能性を調べる。同じ紙の2/3窓を固定乱数で選ぶ4000候補を試し、その後に全1窓変更を1巡回する。穴は追加・復元の両方を許す。

費用は担当商品自身の穴と、全商品16標本の先頭色から区間DPで求める穴埋め利益。独立利益で候補を先に絞り、1列変更の差分DPで確定する。利益係数0.35/0.5を比較する。印刷色と穴の整合、各移動の可視性、最終表示を検査する。

研究用。main.cpp単独は改良元の注文処理で、probe.cppが新しい穴を設計して固定乱数の模擬注文で比較する。隠された注文列を読まず、CLOCK_SCALEを適用する。
''')
