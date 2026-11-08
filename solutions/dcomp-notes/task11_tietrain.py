from pathlib import Path
R=Path(__file__).resolve().parents[2];s=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def rep(a,b):
 global s
 assert s.count(a)==1,(a[:90],s.count(a));s=s.replace(a,b)
code=r'''#ifdef LOCAL_BENCH
    // Research labels only. Copies run the existing request policy on common
    // random future orders; the live policy and its real order stream are untouched.
    inline static bool tie_training_active=false;
    std::string tie_training_log;
    void tie_training_probe(int u,const State& base,const Moves& path,double value,
                            const std::array<double,9>& features) {
        if(tie_training_active || (request_counter-1)%32!=0)return;
        std::vector<TieCand> candidates;
        candidates.push_back({base,path OP_TAG(,{}),value});
        for(const auto& c:tie_pool)if(c.state.order!=base.order && c.value-value<kTieGap)candidates.push_back(c);
        std::stable_sort(candidates.begin()+1,candidates.end(),[](const auto& a,const auto& b){return a.value<b.value;});
        if(candidates.size()>4)candidates.resize(4);
        if(candidates.size()<2)return;
        constexpr int streams=40,horizon=5;
        std::array<std::array<int,horizon>,streams> queries;
        std::mt19937_64 rng(0xa1de08b79ULL+uint64_t(request_counter)*0x9e3779b97f4a7c15ULL+uint64_t(u));
        for(auto& q:queries){int previous=u;for(auto& x:q){x=int(rng()%(P-1));if(x>=previous)++x;previous=x;}}
        tie_training_active=true;
        for(int index=0;index<int(candidates.size());++index) {
            const auto& c=candidates[index];
            restore(c.state);
            const auto f=index?tie_features(c.path.size()):features;
            Solver sim=*this;
            sim.tie_training_log.clear();sim.heavy_log.clear();
            double total=0;
            for(const auto& q:queries) {
                sim.restore(c.state);
                for(int x:q) {
                    const auto moves=sim.process(x);total+=moves.size();
                    if(sim.display()!=A[x] || !sim.fillers_reachable())std::abort();
                }
            }
            tie_training_log+="#t11rf "+std::to_string(request_counter-1)+' '+std::to_string(index)+' '
                +std::to_string(c.path.size())+' '+std::to_string(c.value)+' '
                +std::to_string(c.path.size()+total/streams);
            for(double x:f)tie_training_log+=' '+std::to_string(x);
            tie_training_log+='\n';
        }
        restore(base);tie_training_active=false;
    }
#endif
'''
x='    Moves tie_choice(const State& st0, int u, Moves path OP_TAG(, std::vector<uint8_t>& tags)) {'
rep(x,code+x)
rep('''        const auto f0 = tie_features(path.size());
        int best = -1;''','''        const auto f0 = tie_features(path.size());
#ifdef LOCAL_BENCH
        tie_training_probe(u,c0,path,v0,f0);
#endif
        int best = -1;''')
rep('    cf_report();','''#ifdef LOCAL_BENCH
    std::cerr<<solver.tie_training_log;
#endif
    cf_report();''')
d=R/'solutions/dcomp-t11-tie-train';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n研究用。32注文ごとに、完成plan_costで0.3以内の候補を最大4個、同じランダムな未来40本×5注文で測る。実際の注文列の未来は読まない。コピー上でalt1の方策を実行し、ライブの方策・出力は変えない。#t11rfに元の9特徴、費用、ロールアウト平均を記録する。\n\n教師データはseed0–299で作り、0–199で当てはめ、200–299で比較する。最終の500以降は使わない。実行時間が2秒を超える研究版なので、保存設計replayだけで実行し記録しない。LOCAL_BENCH外では教師作成を行わない。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
