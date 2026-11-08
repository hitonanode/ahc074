    const int lns_mode=std::max(0,env_int("LNS_MODE"));
    const int lns_steps=std::max(0,env_int("LNS_STEPS"))*std::max(1,int(env_real("LNS_MULTIPLIER",1)));
    const int lns_miters=std::max(16,int(env_real("LNS_MAP_ITERS",20000)));
    const int lns_aiters=std::max(1024,int(env_real("LNS_ANNEAL_ITERS",2000000)));
    const int local_finishes=std::max(0,int(env_real("LNS_LOCAL_FINISHES",0)));
    double lns_seconds=0,lns_map_seconds=0,lns_repair_seconds=0;
    int lns_success=0,lns_improved=0;
    const double base_v=best;
    const auto cut_assignment=best_assignment?std::make_unique<Design>(*best_assignment):nullptr;const auto cut_state=state;
    std::cerr<<"@lns_prefix 0 "<<elapsed_sec()<<' '<<best<<'\n';
#ifdef LOCAL_BENCH
    lns_dump_design(state,originalA,1000,best);
#endif
    XorShift lns_rng{0x9d45b6ec31d77201ULL};
    for(int j=0;j<lns_steps && best_assignment;++j){
        const double begin_step=elapsed_sec(),incumbent_v=best,parent_v=lns_mode==6?base_v:best;
        const int id=8+j*(local_finishes+1);
        deval_salt=first_salt+id;
        const auto parent=std::make_unique<Design>(lns_mode==6?*cut_assignment:*best_assignment);
        const auto parent_state=lns_mode==6?cut_state:state;
        LnsRepairStats diag;std::array<bool,256> released{};
        std::unique_ptr<Design> transfer_assignment;DesignState transfer_state;
        double raw_v=0,parent_raw_v=0,raw_model=0,annealed_model=0;
        int destroyed=0,changed_windows=0,after_anneal=0;
        comp.M=M;comp.G=G;comp.edge=parent_state.edge;comp.polarity=parent_state.polarity;comp.rebuild();
        permutation=parent_state.permutation;
        if(lns_mode==1 || lns_mode==6){
            std::ostringstream quiet;auto* old=std::cerr.rdbuf(quiet.rdbuf());
            auto parent_raw=finish(parent.get(),true);
            parent_raw_v=value.from_design(parent_raw);
#ifdef LOCAL_BENCH
            lns_dump_design(parent_raw,originalA,4000+j,parent_raw_v);
            lns_dump_design(parent_state,originalA,5000+j,parent_v);
#endif
            A=parent->A;
            lns_destroy(A,comp,permutation,lns_rng,j);
            for(int w=0;w<G;++w){const auto [a,b]=parent_state.edge[w];const int e=a*(2*M-a-1)/2+b-a-1;
                lns_map.origin_codes[parent_state.permutation[w]]=1+2*e+parent_state.polarity[w];}
            lns_prefer_pairs(*parent,A,comp,lns_rng);diag.preferred_pairs=lns_map.preferred_pairs;
            for(const auto& u:parent->unit)if(u.b>=0)lns_map.old_pairs.emplace_back(u.a,u.b);
            changed_windows=__builtin_popcountll(lns_map.windows);
            const int release_mode=int(env_real("LNS_RELEASE_MODE",0));
            for(const auto& u:parent->unit)if(u.b>=0){
                const bool invalid=!comp.compatible(A[u.a],A[u.b])||(((A[u.a]^A[u.b])>>parent->handle[u.c])&1);
                destroyed+=invalid;
                if((release_mode==1&&invalid)||(release_mode>=2&&((parent->A[u.a]^parent->A[u.b])&lns_map.windows)))released[u.a]=released[u.b]=true;
            }
            if(release_mode==3)released.fill(true);
            const u64 region_windows=lns_map.windows;
            double t=elapsed_sec();
            const auto ws=lns_mode==6?WindowStats{}:assign_windows(A,M,G,comp.edge,comp.polarity,permutation,1e300,lns_miters,0,0.);
            lns_map_seconds+=elapsed_sec()-t;lns_map=LnsMapConfig();comp.rebuild();
            // Outside the destroyed physical region, roles, groups and polarities are exact.
            for(int w=0;w<64;++w)if(!(region_windows>>w&1)){
                assert(permutation[w]==parent_state.permutation[w]);
                if(w<G){assert(comp.edge[w]==parent_state.edge[w]);assert(comp.polarity[w]==parent_state.polarity[w]);}
            }
            diag.map_before=ws.gobj_initial;diag.map_after=ws.gobj_after;diag.map_pairs=ws.matched_pairs;
            std::array<int,64> old_codes{},new_codes{};
            for(int w=0;w<G;++w){
                auto [a,b]=parent_state.edge[w];old_codes[parent_state.permutation[w]]=1+2*(8*a+b)+parent_state.polarity[w];
                auto [c,d]=comp.edge[w];new_codes[permutation[w]]=1+2*(8*c+d)+comp.polarity[w];
            }
            for(int w=0;w<63;++w)diag.window_changes+=old_codes[w]!=new_codes[w];
            diag.lost_max=ws.lost_max;diag.lost_accepted=ws.lost_accepted;diag.lost_tracked=ws.lost_tracked;
            t=elapsed_sec();des=lns_repair(*parent,A,comp,diag,lns_rng.next(),released);
            lns_repair_seconds+=elapsed_sec()-t;std::cerr.rdbuf(old);
            if(!des){
#ifdef LOCAL_BENCH
                lns_dump_design(state,originalA,1001+j,best,true);
                lns_dump_design(parent_state,originalA,2000+j,parent_v,true);
                lns_dump_design(parent_raw,originalA,3000+j,parent_raw_v,true);
#endif
                std::cerr<<"@lns_failure "<<j<<' '<<destroyed<<' '<<diag.broken<<' '<<diag.expanded<<'\n';
                std::cerr<<"@lns_prefix "<<j+1<<' '<<elapsed_sec()<<' '<<best<<'\n';
                lns_seconds+=elapsed_sec()-begin_step;continue;
            }
            raw_model=des->cur/P;
            const int first_segment=std::clamp(int(env_real("LNS_FIRST_SEG",0)),0,3);
            t=elapsed_sec();des->anneal(1e300,lns_aiters*4/(4-first_segment),first_segment,4);
            anneal_sec+=elapsed_sec()-t;total_iters+=des->anneal_iters;
            annealed_model=des->cur/P;after_anneal=lns_new_pairs(*des,*parent);
            old=std::cerr.rdbuf(quiet.rdbuf());auto raw=finish(des.get(),true);std::cerr.rdbuf(old);
            raw_v=value.from_design(raw);
            if(env_int("LNS_TRANSFER_HOLES")){
                transfer_assignment=std::make_unique<Design>(*des);transfer_state=lns_transfer_perforations(raw,parent_state);
            }
#ifdef LOCAL_BENCH
            lns_dump_design(raw,originalA,3000+j,raw_v);
#endif
        }else if(lns_mode==2){
            des=std::make_unique<Design>(*prefix);des->rng.x^=u64(id)*0x9E3779B97F4A7C15ULL;
            double t=elapsed_sec();des->anneal_reheat=2.;des->reheat_start=.5;
            des->anneal(1e300,lns_aiters*2,2,4);
            anneal_sec+=elapsed_sec()-t;total_iters+=des->anneal_iters;
        }else if(lns_mode==5){
            des=std::make_unique<Design>(*parent);des->rng.x^=u64(id)*0x9E3779B97F4A7C15ULL;
            const int first_segment=std::clamp(int(env_real("LNS_REHEAT_FIRST",0)),0,3);
            double t=elapsed_sec();des->anneal(1e300,lns_aiters*4/(4-first_segment),first_segment,4);
            anneal_sec+=elapsed_sec()-t;total_iters+=des->anneal_iters;
        }else if(lns_mode==3){
            des=std::make_unique<Design>(*best_assignment);des->rng.x^=u64(id)*0x9E3779B97F4A7C15ULL;
            warm_state=state;
        }else break;
        double v=complete(id,lns_mode==3?(j%2?2:1):0);
        auto local_assignment=std::make_unique<Design>(*des);auto local_state=last_candidate;
        for(int k=0;k<local_finishes && lns_mode!=3;++k){
            des=std::make_unique<Design>(*local_assignment);
            deval_salt=first_salt+id+k+1;des->rng.x^=u64(id+k+1)*0x9E3779B97F4A7C15ULL;
            warm_state=local_state;
            const double nv=complete(id+k+1,k%2==0?2:1);
            if(nv<v){v=nv;local_assignment=std::make_unique<Design>(*des);local_state=last_candidate;}
        }
        if(transfer_assignment){
            des=std::make_unique<Design>(*transfer_assignment);warm_state=transfer_state;deval_salt=first_salt+6000+j;
            const double nv=complete(6000+j,2);
            if(nv<v){v=nv;local_assignment=std::make_unique<Design>(*des);local_state=last_candidate;}
        }
        des=std::make_unique<Design>(*local_assignment);
#ifdef LOCAL_BENCH
        lns_dump_design(state,originalA,1001+j,best);
        lns_dump_design(local_state,originalA,2000+j,v);
#endif
        ++lns_success;lns_improved+=best<incumbent_v;
        std::cerr<<"@lns_step "<<j<<' '<<lns_mode<<' '<<j%M<<' '<<changed_windows<<' '<<destroyed
                 <<' '<<diag.broken<<' '<<diag.free_targets<<' '<<diag.released_pairs<<' '<<diag.expanded
                 <<' '<<diag.new_pairs<<' '<<after_anneal<<' '<<lns_new_pairs(*des,*parent)
                 <<' '<<parent->cur/P<<' '<<raw_model<<' '<<annealed_model
                 <<' '<<parent_raw_v<<' '<<raw_v<<' '<<parent_v<<' '<<v<<' '<<(v<parent_v)
                 <<' '<<diag.map_before<<' '<<diag.map_after<<' '<<elapsed_sec()-begin_step
                 <<' '<<diag.lost_max<<' '<<diag.lost_accepted<<' '<<diag.lost_tracked
                 <<' '<<diag.window_changes<<' '<<diag.graph_added<<' '<<diag.graph_removed
                 <<' '<<diag.preferred_pairs.size()<<' '<<diag.preferred_valid<<' '<<diag.preferred_used<<'\n';
        lns_seconds+=elapsed_sec()-begin_step;
        std::cerr<<"@lns_prefix "<<j+1<<' '<<elapsed_sec()<<' '<<best<<'\n';
    }
    std::cerr<<"lns_mode = "<<lns_mode<<"\nlns_steps = "<<lns_steps<<"\nlns_success = "<<lns_success
             <<"\nlns_improved = "<<lns_improved<<"\nlns_base_v = "<<base_v<<"\nlns_gain_v = "<<best-base_v
             <<"\nlns_sec = "<<lns_seconds<<"\nlns_map_sec = "<<lns_map_seconds<<"\nlns_repair_sec = "<<lns_repair_seconds<<'\n';
