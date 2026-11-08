        if(lns_mode==4){
            // Equal-compute control: independent repeats of the entire existing
            // map + four-branch + four-refinish pipeline, selected only by V.
            std::ostringstream quiet;auto* output=std::cerr.rdbuf(quiet.rdbuf());
            A=originalA;for(auto& a:A)a&=kActiveWindows;
            std::iota(permutation.begin(),permutation.end(),0);
            const u64 salt=(u64(j)+1)*0x1d42ac9b531ULL;
            std::mt19937_64 rr(779879^salt);comp.init(M,G,rr);lns_map.salt=salt;
            double t=elapsed_sec();
            assign_windows(A,M,G,comp.edge,comp.polarity,permutation,1e300,map_env?map_env:kMapIters,
                           gopt_env?std::max(0,gopt_env):kGoptSteps,0.);
            lns_map_seconds+=elapsed_sec()-t;lns_map=LnsMapConfig();comp.rebuild();
            des=std::make_unique<Design>(A,M,G);des->rng.x^=salt;
            auto est=[&](u64 a,u64 b){const auto reach=comp.closure(a,a^b);u64 r=0;for(int s=0;s<M;++s)r|=u64(reach[s])<<(8*s);return PosetSums::get().both_of(r)/1440.;};
            if(!des->initialize([&](u64 a,u64 b){return comp.compatible(a,b);},est,[](){return false;})){
                std::cerr.rdbuf(output);std::cerr<<"@lns_failure "<<j<<" full_initialize\n";lns_seconds+=elapsed_sec()-begin_step;continue;
            }
            t=elapsed_sec();des->anneal(1e300,anneal_iters,0,2);anneal_sec+=elapsed_sec()-t;total_iters+=des->anneal_iters;
            const auto fresh_prefix=std::make_unique<Design>(*des);std::cerr.rdbuf(output);
            double v=1e100;std::unique_ptr<Design> local_assignment;DesignState local_state;
            auto consider=[&](int cid,int extra){
                const double x=complete(cid,extra);
                if(x<v){v=x;local_assignment=std::make_unique<Design>(*des);local_state=last_candidate;}
            };
            for(int k=0;k<4;++k){
                des=std::make_unique<Design>(*fresh_prefix);des->rng.x^=u64(k)*0x9E3779B97F4A7C15ULL;
                deval_salt=salt+k;t=elapsed_sec();des->anneal_reheat=k?2.:1.;des->reheat_start=.5;
                des->anneal(1e300,int(anneal_iters*.25),2,4);anneal_sec+=elapsed_sec()-t;total_iters+=des->anneal_iters;
                consider(8+8*j+k,0);
            }
            for(int k=0;k<4;++k){
                des=std::make_unique<Design>(*local_assignment);des->rng.x^=u64(1+k/2)*0x9E3779B97F4A7C15ULL;
                deval_salt=salt+4+k;warm_state=local_state;consider(8+8*j+4+k,k%2?2:1);
            }
#ifdef LOCAL_BENCH
            lns_dump_design(state,originalA,1001+j,best);
            lns_dump_design(local_state,originalA,2000+j,v);
#endif
            ++lns_success;lns_improved+=best<parent_v;
            std::cerr<<"@lns_step "<<j<<" 4 0 63 71 71 256 71 0 71 71 71 "<<parent->cur/P
                     <<" 0 0 0 0 "<<parent_v<<' '<<v<<' '<<(v<parent_v)<<" 0 0 "<<elapsed_sec()-begin_step<<'\n';
            lns_seconds+=elapsed_sec()-begin_step;std::cerr<<"@lns_prefix "<<j+1<<' '<<elapsed_sec()<<' '<<best<<'\n';continue;
        }
