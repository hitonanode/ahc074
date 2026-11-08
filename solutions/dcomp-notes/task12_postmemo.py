from pathlib import Path
S=Path(__file__).resolve().parents[1];b=(S/'dcomp-combo-dual25/main.cpp').read_text()
x='''        bool late_memo = get("LATE_MEMO", 1);''';assert b.count(x)==1;b=b.replace(x,x+'\n        bool post_memo = get("POST_MEMO", 1);')
x='''    Moves post_optimize(const State& initial, Moves input_ops,''';assert b.count(x)==1
wrapper='''    // A request-local exact memo for whole ordinary post passes. Neutral collection
    // is excluded: it also updates the caller's candidate pool. The complete input
    // state, path and labels are compared; counters used by the outer repair loops
    // (eject_accepts) are replayed with the saved delta.
    struct PostMemoEntry {
        unsigned epoch=0; int length=0;
        std::array<uint8_t,12*K+32> key;
        State state; Moves path;
        OP_TAG(std::vector<uint8_t> tags;)
        long long eject_delta=0;
        int op=0;
    };
    struct PostMemoTable { unsigned epoch=1; std::array<PostMemoEntry,32> entries; };
    std::shared_ptr<PostMemoTable> post_memo_table;
    inline static long long post_memo_hits=0,post_memo_misses=0;
    Moves post_optimize(const State& initial, Moves input_ops,
                        int u OP_TAG(,std::vector<uint8_t>& tags),bool eject=false,bool delete_only=false) {
        const auto& cfg=search_config();
        if(!cfg.post_memo || neutral_collect || input_ops.empty() || input_ops.size()>2*K ||
           cfg.trace || cfg.predict || cfg.plan_trace
#if F3_PROFILE || COLFAST_PROFILE
           || true
#endif
           ) return post_optimize_impl(initial,std::move(input_ops),u OP_TAG(,tags),eject,delete_only);
        if(!post_memo_table)post_memo_table=std::make_shared<PostMemoTable>();
        auto& table=*post_memo_table;
        std::array<uint8_t,12*K+32> key;
        int length=0;
        std::memcpy(key.data(),order.data(),K);length+=K;
        key[length++]=uint8_t(top_d);key[length++]=uint8_t(fillers.size());
        for(const auto& f:fillers){key[length++]=f.paper;key[length++]=f.lvl;key[length++]=f.hi;}
        key[length++]=eject;key[length++]=delete_only;key[length++]=secondary_neutral;
        key[length++]=input_ops.size()&255;key[length++]=input_ops.size()>>8;
        for(auto [k,d]:input_ops){key[length++]=k;key[length++]=d;}
        OP_TAG(key[length++]=tags.size()&255;key[length++]=tags.size()>>8;
               for(auto t:tags)key[length++]=t;)
        const int padded=(length+7)&~7;std::fill(key.begin()+length,key.begin()+padded,0);
        u64 h0=0xcbf29ce484222325ULL,h1=h0;
        for(int i=0;i<padded;i+=8){u64 word;std::memcpy(&word,key.data()+i,8);
            if(i&8)h1=(h1^word)*0x100000001b3ULL;else h0=(h0^word)*0x100000001b3ULL;}
        const u64 hash=h0^(h1<<23|h1>>41)^u64(length);
        auto& entry=table.entries[(hash^(hash>>32))&31];
        if(entry.epoch==table.epoch && entry.length==length && std::memcmp(entry.key.data(),key.data(),length)==0) {
            ++post_memo_hits;
#ifdef POST_MEMO_CHECK
            const auto before=eject_accepts;
            auto result=post_optimize_impl(initial,std::move(input_ops),u OP_TAG(,tags),eject,delete_only);
            if(result!=entry.path || order!=entry.state.order || top_d!=entry.state.top_d ||
               !same_fillers(fillers,entry.state.fillers) || last_post_operator!=entry.op ||
               eject_accepts-before!=entry.eject_delta OP_TAG(||tags!=entry.tags)) {
                std::cerr<<"POST_MEMO_MISMATCH\\n";std::abort();
            }
            return result;
#else
            post_saved+=int(input_ops.size())-int(entry.path.size());
            eject_accepts+=entry.eject_delta;last_post_operator=entry.op;
            restore(entry.state);OP_TAG(tags=entry.tags;)
            return entry.path;
#endif
        }
        ++post_memo_misses;
        const auto before=eject_accepts;
        auto result=post_optimize_impl(initial,std::move(input_ops),u OP_TAG(,tags),eject,delete_only);
        entry.epoch=table.epoch;entry.length=length;
        std::memcpy(entry.key.data(),key.data(),length);
        entry.state=save();entry.path=result;OP_TAG(entry.tags=tags;)
        entry.eject_delta=eject_accepts-before;entry.op=last_post_operator;
        return result;
    }
    Moves post_optimize_impl(const State& initial, Moves input_ops,'''
b=b.replace(x,wrapper)
x='''        post_context.ready = false;  // all post-processing in this call replays the same st0''';assert b.count(x)==1
b=b.replace(x,'''        if(post_memo_table && ++post_memo_table->epoch==0) {
            for(auto& e:post_memo_table->entries)e.epoch=0;
            post_memo_table->epoch=1;
        }
'''+x)
x='''    cf_report();''';assert b.count(x)==1
b=b.replace(x,'''    std::cerr<<"dp_post_memo_hits = "<<solver.post_memo_hits<<"\\ndp_post_memo_misses = "<<solver.post_memo_misses<<'\\n';
'''+x)
for suffix,prefix in [('', ''),('-check','#define POST_MEMO_CHECK 1\n')]:
 d=S/('dcomp-t12-postmemo'+suffix);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(prefix+b)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-dual25\n\n同じ注文内で、同じ開始state・操作列・ラベル・modeから通常postを繰り返す時だけ完成結果を再利用する。中立候補を収集する呼出しは対象外。完全キーの比較で衝突を排除し、外側の反復条件で使うeject_acceptsの増分を再現する。F3_POST_MEMO=0で無効化でき、trace・profile時も元の計算へ戻す。チェック版はhitを元関数で全て再計算して、出力・完成state・eject増分を比較する。\n\nCLOCK_SCALE、固定探索予算、両コンパイラ同じ探索量、@paper/@ops、ログ・実験switch・段・DesignStoreを保持する。\n')
