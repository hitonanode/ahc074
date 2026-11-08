"""Fixed-budget successive halving: six short branches, finish four by raw V."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/dcomp-climb-cache/main.cpp').read_text()
a='''    for(int i=0;i<candidates;++i) {
        deval_salt=first_salt+i;
        des=std::make_unique<Design>(*prefix);
        if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();des->anneal_reheat=i?2:1.;des->reheat_start=shared/4.;
        des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        complete(i,0);
    }'''
b='''    // Same total branch iterations, with six shallower raw states. Raw V is
    // only a screening predictor: four survivors still receive the entire
    // native finishing and compete by completed-design V.
    constexpr int raw_count=6;
    std::array<std::unique_ptr<Design>,raw_count> raw_designs;
    std::array<std::pair<double,int>,raw_count> raw_scores;
    double screen_sec=0;
    for(int i=0;i<raw_count;++i) {
        deval_salt=first_salt+i;
        des=std::make_unique<Design>(*prefix);
        if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();des->anneal_reheat=i?2:1.;des->reheat_start=shared/4.;
        des->anneal(1e300,int(anneal_iters*branch_scale*candidates/raw_count),shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        begin=elapsed_sec();
        std::ostringstream raw_log;auto* old=std::cerr.rdbuf(raw_log.rdbuf());
        auto raw_state=finish(des.get(),true,0);
        std::cerr.rdbuf(old);
        const double score=raw_state.emergency?1e100:value.from_design(raw_state);
        raw_scores[i]={score,i};raw_designs[i]=std::move(des);
        screen_sec+=elapsed_sec()-begin;
    }
    auto ranking=raw_scores;std::sort(ranking.begin(),ranking.end());
    std::array<bool,raw_count> survives{};
    for(int j=0;j<candidates;++j)survives[ranking[j].second]=true;
    int survivor=0;
    for(int i=0;i<raw_count;++i) {
        std::cerr<<"@dc_rawbranch "<<i<<' '<<raw_scores[i].first<<' '<<survives[i]<<'\\n';
        if(!survives[i])continue;
        deval_salt=first_salt+i;des=std::move(raw_designs[i]);
        complete(survivor++,0);
    }
    std::cerr<<"dc_screen_sec = "<<screen_sec<<'\\n';'''
assert s.count(a)==1;s=s.replace(a,b)
p=ROOT/'solutions/dcomp-halving6';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-climb-cache（その元はlegal-tie-fast）

共有prefixは元のまま、その後の総anneal反復数を6枝へ等分する。各枝の未仕上げ設計をVで評価し、上位4枝だけ元のfiller climb・rematch・穿孔・後段rematchまで仕上げる。従来の4回の再仕上げも保ち、完成した8候補からVで最終選択する。Vの学習は変更しない。

すべて固定反復数・固定乱数。生のVは仕上げ後を完全には予測しないため、完成設計の8列リプレイで有効性を判断する。注文処理はlegal-tie-fastのまま。時間による切替なし。dc_screen_secは仕上げ前の6候補の選別時間、@dc_rawbranchは枝番号・生のV・通過フラグ。
''')
