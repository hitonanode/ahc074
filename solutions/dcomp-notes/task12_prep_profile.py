from pathlib import Path
S=Path(__file__).resolve().parents[1]
b=(S/'dcomp-t12-profile/main.cpp').read_text()
x='    template <class Evaluate,class Prepare,class Screen>\n'
fields='''    struct PrepKey { std::array<u64,3> moved{}; unsigned epoch=0; };
    std::array<PrepKey,128> prep_seen{};
    unsigned prep_epoch=1;
    long long prep_calls=0,prep_hits=0;
    double prep_sec=0,prep_hit_sec=0;
'''
assert b.count(x)==1;b=b.replace(x,fields+x)
x='''        const auto accepts_at_start = eject_accepts;
        // The papers''';assert b.count(x)==1
b=b.replace(x,'''        const auto accepts_at_start = eject_accepts;
        std::array<u64,3> prep_mask{};
        for(const auto& e:base_edits)prep_mask[e.paper>>6]|=u64(1)<<(e.paper&63);
        const u64 ph=(prep_mask[0]^(prep_mask[1]<<19|prep_mask[1]>>45)^(prep_mask[2]<<41|prep_mask[2]>>23))*0x9e3779b97f4a7c15ULL;
        auto& seen_prep=prep_seen[(ph^(ph>>32))&127];
        const bool prep_hit=seen_prep.epoch==prep_epoch && seen_prep.moved==prep_mask;
        seen_prep={prep_mask,prep_epoch};++prep_calls;prep_hits+=prep_hit;
        const double prep_start=elapsed_sec();
        // The papers''')
x='''        auto& trial = eject_trial;''';assert b.count(x)==2
b=b.replace(x,'''        const double prep_time=elapsed_sec()-prep_start;
        prep_sec+=prep_time;if(prep_hit)prep_hit_sec+=prep_time;
        auto& trial = eject_trial;''',1)
x='''        post_context.ready = false;  // all post-processing in this call replays the same st0''';assert b.count(x)==1
b=b.replace(x,'''        if(++prep_epoch==0){for(auto& x:prep_seen)x.epoch=0;prep_epoch=1;}
'''+x)
x='''    cf_report();''';assert b.count(x)==1
b=b.replace(x,'''    std::cerr<<"dp_prep_calls = "<<solver.prep_calls<<"\\ndp_prep_hits = "<<solver.prep_hits
        <<"\\ndp_prep_sec = "<<solver.prep_sec<<"\\ndp_prep_hit_sec = "<<solver.prep_hit_sec<<'\\n';
'''+x)
d=S/'dcomp-t12-prep-prof';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(b)
(d/'README.md').write_text('改良元: solutions/dcomp-t12-profile\n\neject修復の候補紙の準備だけを計測する。同じ注文と移動紙集合の再計算が何回・何秒あるかを128slotで数える。省略は行わず、計算と結果は同じ。時計はscaled elapsed_sec、探索予算へ使わない。ログ・段と目次・実験switch・DesignStoreを保持する。\n')
# Adapt the previous passive duplicate measurement, preserving both secondary modes in its key.
s=(S/'dcomp-notes/task11_postduplicate.py').read_text()
s=s.replace("solutions/dcomp-combo-alt1/main.cpp","solutions/dcomp-combo-dual25/main.cpp").replace("dcomp-t11-postdup-prof","dcomp-t12-postdup-prof")
s=s.replace('bool eject,only,collect;','bool eject,only,collect,secondary;')
s=s.replace('old.collect!=neutral_collect ||','old.collect!=neutral_collect || old.secondary!=secondary_neutral ||')
s=s.replace('eject,delete_only,neutral_collect});','eject,delete_only,neutral_collect,secondary_neutral});')
s=s.replace('改良元: solutions/dcomp-combo-alt1','改良元: solutions/dcomp-combo-dual25')
exec(compile(s,str(S/'dcomp-notes/task12_prep_profile.py'),'exec'))
