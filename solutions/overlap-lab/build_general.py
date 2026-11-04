from pathlib import Path
root=Path(__file__).resolve().parent
source=(root.parent/"module-lab/module.cpp").read_text().split("int main(int argc, char** argv)")[0]
source=source.replace("double access_probability = 0.2;", """double access_probability = 0.2;
    int generic_windows=1, generic_papers=2, full_patterns=0, handle_patterns=0, controls=0;
    std::vector<double> probabilities;""")
source=source.replace("vis.resize(M.S);", """generic_windows=arg_i("G",1);generic_papers=arg_i("M",2);
        full_patterns=1<<M.N;handle_patterns=1<<arg_i("H",2);controls=full_patterns+handle_patterns;
        probabilities.resize(controls+M.K);vis.resize(M.S);""")
source=source.replace("rest.assign(8 + M.K, {});", "rest.assign(controls + M.K, {});")
source=source.replace("rest[8 + paper].push_back(s);", "rest[controls + paper].push_back(s);")
source=source.replace("rest[display].push_back(s);", "rest[display].push_back(s);\n            if(!(display>>(generic_windows+arg_i(\"H\",2))))rest[full_patterns+((display>>generic_windows)&(handle_patterns-1))].push_back(s);")
source=source.replace("for (const auto& v : rest) infeasible += v.empty();", "for(int t=0;t<int(rest.size());t++)if(probabilities[t]>0)infeasible+=rest[t].empty();")
source=source.replace("for (int paper=0; paper<K; ++paper)", "for (int paper=generic_papers; paper<K; ++paper)")
source=source.replace("if (t < 8) { propagate(rest[t]); return; }", "if (t < controls) { propagate(rest[t]); return; }")
source=source.replace("const int paper = t - 8;", "const int paper = t - controls;")
source=source.replace("for (int t = 0; t < 8 + M.K; ++t)", "for (int t = 0; t < controls + M.K; ++t)")
source=source.replace("const double probability = t < 8 ? (1-access_probability)/8 : access_probability/M.K;", "const double probability=probabilities[t];if(probability==0)continue;")
source+=r'''
int main(int argc,char** argv) {
    for(int i=1;i<argc;i++){std::string s=argv[i];auto j=s.find('=');if(j!=s.npos)g_args[s.substr(0,j)]=s.substr(j+1);}
    int G=arg_i("G",1),MG=arg_i("M",2),H=arg_i("H",2),K=arg_i("K",MG+2*H),seed=arg_i("seed",1),iterations=arg_i("iters",2000);
    double q=arg_d("q",.1),gprob=arg_d("gprob",.5),seconds=arg_d("seconds",300);
    bool triangle=arg_i("triangle",0),lock_generic=arg_i("lock_generic",1),lock_body=arg_i("lock_body",0);
    int guard=arg_i("guard",0),code_bits=guard==2?G:guard?1:0;
    int body_mask=((1<<code_bits)-1)<<(G+H);
    if(G!=MG*(MG-1)/2)return 2;
    Model model;model.T=(1<<(G+H+code_bits))+(1<<H)+K;model.build(G+H+code_bits,K);
    Design design;design.op.resize(K);design.bk.resize(K);
    std::vector<int> full_color(K),counts(H);std::mt19937_64 rng(seed);
    int j=0;for(int a=0;a<MG;a++)for(int b=a+1;b<MG;b++) {
        design.op[a]|=1ULL<<j;design.op[b]|=1ULL<<j;design.bk[b]|=1ULL<<j;j++;
    }
    if(guard==2){int z=G+H;for(int a=0;a<MG;a++)for(int b=a+1;b<MG;b++){design.op[a]|=1ULL<<z;design.op[b]|=1ULL<<z;z++;}}
    else if(guard)for(int a=0;a<MG;a++)design.op[a]|=1ULL<<(G+H);
    auto generic_op=design.op,generic_black=design.bk;
    std::vector<int> allowed_g,perm(MG);std::iota(perm.begin(),perm.end(),0);
    do{u64 covered=0,display=0;for(int x:perm){display|=design.bk[x]&~covered;covered|=design.op[x];}allowed_g.push_back(display);}while(std::next_permutation(perm.begin(),perm.end()));
    for(int k=0;k<MG;k++)full_color[k]=design.bk[k];
    for(int k=MG;k<K;k++) {
        int c=(k-MG)*H/(K-MG);
        full_color[k]=(rng()&((1<<(G+H))-1))&~(1<<(G+c));
        full_color[k]|=(counts[c]++&1)<<(G+c);
        full_color[k]|=body_mask;
        design.op[k]=((1<<(G+c+1))-1)|body_mask;design.bk[k]=full_color[k]&design.op[k];
    }
    rng.seed(arg_i("search_seed",seed));
    Evaluator ev(model,1000);ev.access_probability=q;ev.full_color=full_color;
    for(int h=0;h<(1<<H);h++) {
        for(int g:allowed_g)ev.probabilities[g|(h<<G)]+=(1-q)*gprob/((1<<H)*allowed_g.size());
        ev.probabilities[ev.full_patterns+h]=(1-q)*(1-gprob)/(1<<H);
    }
    for(int k=MG;k<K;k++)ev.probabilities[ev.controls+k]=q/(K-MG);
    ev.prepare(design);if(ev.infeasible)return 3;
    double baseline=ev.solve(300,1e-5,.6),baseline_lo=ev.g_lo,baseline_hi=ev.g_hi;
    double current=baseline,best=baseline;Design best_design=design;
    std::vector<int> chain(H);for(int i=0;i<H;i++)chain[i]=((1<<(G+i+1))-1)|body_mask;
    double start=now_sec();int completed=0,accepted=0;
    std::cerr<<"baseline "<<baseline<<" gap "<<ev.g_hi-ev.g_lo<<'\n';
    for(int it=0;it<iterations;it++) {
        double progress=std::max(double(it)/iterations,(now_sec()-start)/seconds);if(progress>=1)break;
        Design proposal=design;auto next_chain=chain;
        if(triangle) {
            if(rng()%8==0) {
                int a=G+rng()%H,b=G+rng()%H;
                auto swap=[&](unsigned mask){bool change=((mask>>a)^(mask>>b))&1;return mask^(unsigned(change)<<a)^(unsigned(change)<<b);};
                for(int& c:next_chain)c=swap(c);for(int k=MG;k<K;k++)proposal.op[k]=swap(proposal.op[k]);
            }else proposal.op[MG+rng()%(K-MG)]=chain[rng()%H];
        } else {
            int k=rng()%K,j=rng()%(G+H);
            if(k<MG){if(lock_generic)j=G+rng()%H;proposal.set(k,j,rng()%3);}
            else{if(lock_body)j=G+rng()%H;proposal.op[k]^=1ULL<<j;}
        }
        for(int k=MG;k<K;k++)proposal.bk[k]=full_color[k]&proposal.op[k];
        auto old_h=ev.h;ev.prepare(proposal);if(ev.infeasible){ev.h=std::move(old_h);continue;}
        double value=ev.solve(10,2e-4,.6);if(ev.g_hi-ev.g_lo>.002)value=ev.solve(60,2e-4,.6);
        double temp=.025*std::pow(.008,progress),coin=(rng()>>11)*0x1.0p-53;
        if(value<current||coin<std::exp((current-value)/temp)) {
            design=std::move(proposal);chain=std::move(next_chain);current=value;accepted++;
            if(value<best-.0002){value=ev.solve(200,1e-5,.6);current=value;if(value<best){best=value;best_design=design;std::cerr<<"best "<<it<<' '<<best<<" elapsed "<<now_sec()-start<<'\n';}}
        } else ev.h=std::move(old_h);
        completed=it+1;
    }
    ev.prepare(best_design);std::fill(ev.h.begin(),ev.h.end(),0);best=ev.solve(400,1e-5,.6);
    std::cout<<"{\"G\":"<<G<<",\"M\":"<<MG<<",\"H\":"<<H<<",\"K\":"<<K<<",\"seed\":"<<seed<<",\"triangle\":"<<triangle
        <<",\"guard\":"<<guard<<",\"lock_generic\":"<<lock_generic<<",\"lock_body\":"<<lock_body<<",\"q\":"<<q<<",\"gprob\":"<<gprob
        <<",\"baseline\":"<<baseline<<",\"baseline_lo\":"<<baseline_lo<<",\"baseline_hi\":"<<baseline_hi<<",\"best\":"<<best<<",\"best_lo\":"<<ev.g_lo<<",\"best_hi\":"<<ev.g_hi
        <<",\"iterations\":"<<completed<<",\"accepted\":"<<accepted<<",\"elapsed\":"<<now_sec()-start<<",\"colors\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<full_color[k];std::cout<<"],\"opaque\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<best_design.op[k];std::cout<<"],\"black\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<best_design.bk[k];std::cout<<"]}\n";
}
'''
(root/"general.cpp").write_text(source)
