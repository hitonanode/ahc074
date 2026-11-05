"""Reproducible pipeline-only variants of esw-clean. No shared files are edited."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=(ROOT/'solutions/esw-clean/main.cpp').read_text()

def emit(name,src,readme):
    target=ROOT/'solutions'/name
    target.mkdir(exist_ok=True)
    (target/'main.cpp').write_text(src)
    (target/'README.md').write_text('改良元: solutions/esw-clean\n\n'+readme+'\n')

cap_code=r'''
// ==== Design pipeline: choosing the cap before columns exist ====

// Keep every generic window and its comparator unchanged. Each of the remaining
// 26 windows can be the cap, so this choice never breaks a compatible pair.
// Choose by the same 71-pair greedy objective as assign_windows, then canonicalize
// the chosen cap to internal window 63. The later design optimizes the columns.
void frame_choose_cap(std::vector<u64>& A, const std::vector<u64>& original,
                      const Comparator& comp, std::vector<int>& permutation) {
    const auto start=Clock::now();
    const char* setting=std::getenv("FRAME_CAP");
    if(setting && std::atoi(setting)==0) return;
    struct Edge { int a,b; u64 diff; int generic; };
    std::vector<Edge> edges;
    std::vector<u64> full=A;
    for(int u=0;u<P;++u) full[u]|=((original[u]>>permutation[63])&1)<<63;
    for(int a=0;a<P;++a) for(int b=a+1;b<P;++b) {
        const u64 diff=full[a]^full[b];
        if(__builtin_popcountll(diff)>26) continue;
        const auto reach=comp.closure(full[a],diff);u64 rel=0;
        for(int j=0;j<comp.M;++j) rel|=u64(reach[j])<<(8*j);
        if(rel&kDiagonal)continue;
        edges.push_back({a,b,diff,5*PosetSums::get().both_of(rel)});
    }
    const int need=256-(191-comp.M);
    auto value=[&](int cap) {
        std::vector<std::pair<int,int>> keys;
        const u64 hm=~low_bits(comp.G)&~(1ULL<<cap);
        for(int i=0;i<int(edges.size());++i) {
            const auto& e=edges[i];
            const int key=1800*__builtin_popcountll(e.diff&hm)+e.generic
                +144*__builtin_popcountll(e.diff&~(1ULL<<cap));
            keys.emplace_back(key,i);
        }
        std::sort(keys.begin(),keys.end());
        std::array<bool,P> used{};long long sum=0;int n=0;
        for(auto [key,i]:keys) {
            const auto& e=edges[i];if(used[e.a]||used[e.b])continue;
            used[e.a]=used[e.b]=true;sum+=key;
            if(++n==need)break;
        }
        return double(sum)/(3600*need)+10*(need-n);
    };
    int chosen=63;const double before=value(63);double best=before;
    for(int c=comp.G;c<63;++c) {
        const double now=value(c);
        if(now<best-1e-9){best=now;chosen=c;}
    }
    if(chosen!=63) std::swap(permutation[chosen],permutation[63]);
    for(int u=0;u<P;++u) {
        u64 a=full[u];
        const u64 flip=((a>>chosen)^(a>>63))&1;
        a^=(flip<<chosen)|(flip<<63);A[u]=a&kActiveWindows;
    }
    std::cerr<<"frame_cap_changed = "<<(chosen!=63)
             <<"\nframe_cap_before = "<<before<<"\nframe_cap_after = "<<best
             <<"\nframe_cap_gain = "<<best-before<<"\nframe_cap_sec = "<<scaled_since(start)<<'\n';
}

'''
s=BASE.replace('//   Design iteration counts\n','//   Design pipeline: choosing the cap before columns exist\n//   Design iteration counts\n')
s=s.replace('// ==== Design iteration counts ====\n',cap_code+'// ==== Design iteration counts ====\n')
s=s.replace('        comp.rebuild();\n        des = std::make_unique<Design>(A, M, G);',
'''        comp.rebuild();
        frame_choose_cap(A, originalA, comp, permutation);
        des = std::make_unique<Design>(A, M, G);''')
s=s.replace('A[u] |= originalA[u] & kCapBit;', 'A[u] |= ((originalA[u] >> permutation[63]) & 1) << 63;')
s=s.replace('<< "cap_window = " << kCapWindow', '<< "cap_window = " << permutation[63]')
emit('design-frame-cap',s,
'''窓の割当の直後・列配置の前に、汎用窓以外の26窓から cap を選ぶ。
比較器とその可解な対は固定し、cap を除いたハンドル差を使う71対の貪欲費用が最小の窓を選ぶ。
その後は通常どおり全ての列・ハンドル順・共有対を最適化する。
既存の列を修復する cap 交換とは異なり、この時点では列がないので修復は不要。

選んだ物理窓を内部の窓63へ移し、DesignStore の permutation と A も整合させる。
FRAME_CAP=0 で無効。通常のログ・設定・プロファイラ・紙属性・操作ラベルは維持する。
追加指標は frame_cap_changed、frame_cap_before / after / gain（割当の目的値）、frame_cap_sec。
既存の cap_window は最終的な物理窓番号を表す。gobj_after は cap 選択前の従来の値。''')

mid_code=r'''
// ==== Design pipeline: target reassignment between annealing segments ====

// Spend two of the four existing Hungarian rounds halfway through the anneal.
// Temperature slices and iteration counts are the same as Design::anneal. The
// following segments can rearrange columns after the global target assignment.
MatchStats frame_anneal(Design& d,int iterations) {
    const char* rounds_env=std::getenv("FRAME_MID_ROUNDS");
    const char* after_env=std::getenv("FRAME_MID_AFTER");
    const int rounds=rounds_env?std::clamp(std::atoi(rounds_env),0,4):2;
    const int after=after_env?std::clamp(std::atoi(after_env),1,3):2;
    MatchStats mid;
    if(!rounds){d.anneal(1e300,iterations);return mid;}
    int total=0;
    for(int s=0;s<Design::kAnnealSegments;++s) {
        d.refresh_reset();
        const int count=iterations/Design::kAnnealSegments;
        const double p0=double(s)/Design::kAnnealSegments,p1=double(s+1)/Design::kAnnealSegments;
        if(d.H<=32) Design::Annealer<4>(d).run(1e9,count,p0,p1);
        else Design::Annealer<5>(d).run(1e9,count,p0,p1);
        total+=d.anneal_iters;
        if(s+1==after)mid=rematch_probability(d,rounds,1.0,2.0);
    }
    d.anneal_iters=total;
    std::cerr<<"frame_mid_iterations = "<<mid.iterations<<"\nframe_mid_cycles = "<<mid.accepted_cycles
             <<"\nframe_mid_changed = "<<mid.changed<<"\nframe_mid_decrease = "<<mid.decrease
             <<"\nframe_mid_sec = "<<mid.seconds<<'\n';
    return mid;
}

'''
s=BASE.replace('//   Design iteration counts\n','//   Design pipeline: target reassignment between annealing segments\n//   Design iteration counts\n')
s=s.replace('// ==== Design iteration counts ====\n',mid_code+'// ==== Design iteration counts ====\n')
s=s.replace('    des->anneal(1e300, anneal_iters);','    const auto frame_mid = frame_anneal(*des, anneal_iters);')
s=s.replace('rematch_probability(*des, kMatchIterations, 1.0, 2.0);',
            'rematch_probability(*des, std::max(0, kMatchIterations - frame_mid.iterations), 1.0, 2.0);')
emit('design-frame-midmatch',s,
'''設計の焼きなまし4区間のうち、第2区間の直後に Hungarian 再割り当てを2回行う。
最後の再割り当ては2回とし、合計4回、焼きなましの温度と候補数は維持する。
一括の目標交換が作った状態から、後ろ2区間で列・ハンドル順も適応させる。

FRAME_MID_ROUNDS（既定2、0で基準の順序）と FRAME_MID_AFTER（既定2、1～3）で位置を指定できる。
追加指標 frame_mid_iterations / cycles / changed / decrease / sec は途中の再割り当て。
従来の match_* は最後の分で、回数は両者を合わせる。その他のログ・設定・プロファイラは維持する。''')

begin=BASE.index('    if (climb_iters > 0) des->filler_climb(1e300, climb_iters);')
end=BASE.index('    const auto match = rematch_probability',begin)
climb=BASE[begin:end]
insert=BASE.index('    // Restore the cap bit only',end)
s=BASE[:begin]+BASE[end:insert]+climb+BASE[insert:]
s=s.replace('    const auto match = rematch_probability(*des, kMatchIterations, 1.0, 2.0);',
'''    // Let the restricted filler climb optimize the heads of the reassigned design.
    const auto match = rematch_probability(*des, kMatchIterations, 1.0, 2.0);''')
emit('design-frame-postclimb',s,
'''後段の順序を Hungarian 再割り当て4回 → filler climb 154,000回にする。
再割り当てが変更した対・目標配置に合わせて、最後にフィラーの列交換を行う。
各段の回数・重みは変えない。穿孔は最後に行う。

新しい設定や指標はない。match_end_sec が climb_end_sec より先になる。
全ての既存ログ・設定・プロファイラ・DesignStore・紙属性・操作ラベルを維持する。''')

# Exact speedup: reuse the constructor's value and compute only matrix entries
# which survive the color/compatibility screening. target() is pure and >= 0.
s=BASE.replace('    double strength;\n    ProbabilityHead(', '    double strength;\n    double last_value = 0;\n    ProbabilityHead(')
start=s.index('struct ProbabilityHead {')
end=s.index('// ==== Helper tables:',start)
part=s[start:end]
part=part.replace('        return sum;\n    }\n};\n// Reassign',
                  '        return last_value = sum;\n    }\n};\n// Reassign')
part=part.replace('double initial = d.cur - weight * head.rebuild(), merit = initial;',
                  'double initial = d.cur - weight * head.last_value, merit = initial;')
part=part.replace('single_target(P, std::vector<double>(d.H)),',
                  'single_target(P, std::vector<double>(d.H, -1)),')
part=part.replace('            for (int c = 0; c < d.H; c++) single_target[a][c] = head.target(a, {a, -1, c});\n','')
part=part.replace('                    profit = single_target[b][c];',
'''                    // Only mobile targets and allowed singleton colors enter the matrix.
                    // The state is fixed while building it, so deferred evaluation is exact.
                    auto& target_profit = single_target[b][c];
                    if (target_profit < 0) target_profit = head.target(b, {b, -1, c});
                    profit = target_profit;''')
s=s[:start]+part+s[end:]
assert 'return last_value = sum;' in s
emit('design-frame-lazy',s,
'''Hungarian 再割り当ての計算だけを省き、設計・乱数・操作列を維持する。

- ProbabilityHead の構築直後、同じ状態で2回目の全再計算をしていた箇所を、構築時の戻り値の再利用にする。
- 単独紙に目標を割り当てる利益は、色・整合の検査を通って費用行列に入る (目標, 列) だけ計算し、再利用する。
  head.target は状態を変更せず値が非負なので、未計算を −1 で表す。

新しいスイッチ・指標はない。AF_PROFILE の関数呼出回数は不要な計算を除いた分だけ減る。
その他の全ログ・設定・プロファイラ・DesignStore・紙属性・操作ラベルを維持する。''')

# A pipeline objective: price how much the next stage can save by putting
# frequently differing handle windows deeper. The proposal machinery is intact.
s=BASE
s=s.replace('    const int np = pairs.n, np8 = pairs.n8;',
'''    const int np = pairs.n, np8 = pairs.n8;
    const char* frame_weight_env = std::getenv("FRAME_ORDER_WEIGHT");
    const double frame_order_weight = frame_weight_env ? std::atof(frame_weight_env) : 0.5;''')
needle='        return double(total) / (need * 3600) + (need - matched) * 10.0;'
assert s.count(needle)==1
s=s.replace(needle,r'''        double order_correction = 0;
        if (frame_order_weight != 0 && matched == need) {
            // The next stage chooses a common order of the handles. Approximate
            // P(pair-column >= j) by a linear tail and normalize it to mean 0.5.
            // With counts equal this is the old price; concentrated differences
            // can be hidden by putting those windows deeper in the columns.
            std::array<int,64> frequency{}, sorted_frequency{};
            int sum = 0, count = 0;
            for (int p : candidate_selected)
                for (u64 z = pairs.diff[p] & handle_mask; z; z &= z-1) {
                    ++frequency[__builtin_ctzll(z)]; ++sum;
                }
            for (u64 z = handle_mask; z; z &= z-1)
                sorted_frequency[count++] = frequency[__builtin_ctzll(z)];
            std::sort(sorted_frequency.begin(),sorted_frequency.begin()+count);
            double weighted = 0;
            for (int j=0;j<count;++j) weighted += sorted_frequency[j]*(count-j);
            order_correction = frame_order_weight*(weighted/(count+1)-0.5*sum)/need;
        }
        return double(total) / (need * 3600) + (need - matched) * 10.0 + order_correction;''')
emit('design-frame-ordercost',s,
'''窓の割当が選んだ71対に対し、後段でハンドル順を最適化できる価値を目的関数へ加える。
各ハンドルで違う対の数を数え、違いの少ない窓を浅く、多い窓を深く置いた場合の費用を近似する。
対の列が深さ j 以降にある確率を線形の尾で近似し、平均重みが従来の0.5になるよう正規化する。
従来の一様費用との差を0.5倍して gobj に加える。全窓の違い数が同じなら補正は0。

FRAME_ORDER_WEIGHT（既定0.5、0で無効）。探索の提案・事前除外・乱数・後段の設計は変えない。
MAP_ITERS / GOPT_STEPS で時間を合わせられる。gobj_before / after には新しい補正も含む。
全ての既存ログ・設定・プロファイラ・DesignStore・紙属性・操作ラベルを維持する。''')

# Match the extra cost of the order objective with a shorter assignment search.
s_fast=s.replace('kMapIters = int(450000', 'kMapIters = int(342000').replace('kGoptSteps = int(133000', 'kGoptSteps = int(101080')
assert s_fast != s
emit('design-frame-orderfast',s_fast,
'''design-frame-ordercost と同じ、ハンドル順の価値を加えた割当目的関数を使う。
追加の評価費用を賄うため、窓割当の反復回数を基準の76%（342,000回 + climb 101,080回）にする。
その他の段の回数は基準と同じ。FRAME_ORDER_WEIGHT（既定0.5）、MAP_ITERS / GOPT_STEPS を使用できる。
その他のログ・設定・プロファイラ・DesignStore・紙属性・操作ラベルを維持する。''')

s_balanced=s.replace('kMapIters = int(450000', 'kMapIters = int(369000').replace('kGoptSteps = int(133000', 'kGoptSteps = int(109060')
emit('design-frame-balanced',s_balanced,
'''design-frame-ordercost と同じ、ハンドル順の価値を加えた割当目的関数を使う。
追加の評価費用を賄うため、窓割当の反復回数を基準の82%（369,000回 + climb 109,060回）にする。
その他の段の回数は基準と同じ。FRAME_ORDER_WEIGHT（既定0.5）、MAP_ITERS / GOPT_STEPS を使用できる。
その他のログ・設定・プロファイラ・DesignStore・紙属性・操作ラベルを維持する。''')
