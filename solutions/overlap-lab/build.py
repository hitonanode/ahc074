from pathlib import Path

root=Path(__file__).resolve().parent
source=(root.parent/"module-lab/module.cpp").read_text()
source=source[:source.index("int main(int argc, char** argv)")]
source=source.replace("double access_probability = 0.2;", "double access_probability = 0.2, generic_probability = 0.5;\n    int full_patterns=0, handle_patterns=0, controls=0;")
source=source.replace("vis.resize(M.S);", "full_patterns=1<<M.N;handle_patterns=1<<(M.N-1);controls=full_patterns+handle_patterns;\n        vis.resize(M.S);")
source=source.replace("rest.assign(8 + M.K, {});", "rest.assign(controls + M.K, {});")
source=source.replace("rest[8 + paper].push_back(s);", "rest[controls + paper].push_back(s);")
source=source.replace("rest[display].push_back(s);", "rest[display].push_back(s);\n            rest[full_patterns+(display>>1)].push_back(s);")
source=source.replace("for (const auto& v : rest) infeasible += v.empty();", "for(int t=0;t<int(rest.size());t++)if(t!=controls&&t!=controls+1)infeasible+=rest[t].empty();")
source=source.replace("for (int paper=0; paper<K; ++paper)", "for (int paper=2; paper<K; ++paper)")
source=source.replace("if (t < 8) { propagate(rest[t]); return; }", "if (t < controls) { propagate(rest[t]); return; }")
source=source.replace("const int paper = t - 8;", "const int paper = t - controls;")
source=source.replace("for (int t = 0; t < 8 + M.K; ++t)", "for (int t = 0; t < controls + M.K; ++t)")
source=source.replace("const double probability = t < 8 ? (1-access_probability)/8 : access_probability/M.K;", """if(t==controls||t==controls+1)continue;
            const double probability=t<full_patterns?(1-access_probability)*generic_probability/full_patterns:
                t<controls?(1-access_probability)*(1-generic_probability)/handle_patterns:access_probability/(M.K-2);""")
source+=r'''
int main(int argc,char** argv) {
    for(int i=1;i<argc;i++){std::string s=argv[i];auto j=s.find('=');if(j!=s.npos)g_args[s.substr(0,j)]=s.substr(j+1);}
    int H=arg_i("H",2),K=arg_i("K",2+2*H),seed=arg_i("seed",1),iterations=arg_i("iters",2000);
    double q=arg_d("q",.1),gprob=arg_d("gprob",.5),seconds=arg_d("seconds",120);
    bool triangle=arg_i("triangle",0);
    Model model;model.T=(1<<(H+1))+(1<<H)+K;model.build(H+1,K);
    Design design;design.op.resize(K);design.bk.resize(K);
    std::vector<int> full_color(K),counts(H);std::mt19937_64 rng(seed);
    for(int k=0;k<2;k++){design.op[k]=1;design.bk[k]=k;full_color[k]=k;}
    for(int k=2;k<K;k++) {
        int c=(k-2)*H/(K-2);
        full_color[k]=(rng()&((1<<(H+1))-1))&~(1<<(c+1));
        full_color[k]|=(counts[c]++&1)<<(c+1);
        design.op[k]=(1<<(c+2))-1;design.bk[k]=full_color[k]&design.op[k];
    }
    rng.seed(arg_i("search_seed",seed));
    Evaluator ev(model,1000);ev.access_probability=q;ev.generic_probability=gprob;ev.full_color=full_color;
    ev.prepare(design);double baseline=ev.solve(300,1e-5,.6),baseline_lo=ev.g_lo,baseline_hi=ev.g_hi;
    double current=baseline,best=baseline;Design best_design=design;
    std::vector<int> chain(H);for(int i=0;i<H;i++)chain[i]=(1<<(i+2))-1;
    double start=now_sec();int completed=0,accepted=0;
    std::cerr<<"baseline "<<baseline<<" gap "<<ev.g_hi-ev.g_lo<<'\n';
    for(int it=0;it<iterations;it++) {
        double progress=std::max(double(it)/iterations,(now_sec()-start)/seconds);if(progress>=1)break;
        Design proposal=design;auto next_chain=chain;
        if(triangle) {
            if(rng()%8==0) {
                int a=1+rng()%H,b=1+rng()%H;
                auto swap=[&](unsigned mask){bool change=((mask>>a)^(mask>>b))&1;return mask^(unsigned(change)<<a)^(unsigned(change)<<b);};
                for(int& c:next_chain)c=swap(c);for(int k=2;k<K;k++)proposal.op[k]=swap(proposal.op[k]);
            }else proposal.op[2+rng()%(K-2)]=chain[rng()%H];
        } else {
            int k=rng()%K,j=rng()%(H+1);
            if(k<2)proposal.set(k,j,rng()%3);
            else proposal.op[k]^=1ULL<<j;
        }
        for(int k=2;k<K;k++)proposal.bk[k]=full_color[k]&proposal.op[k];
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
    std::cout<<"{\"H\":"<<H<<",\"K\":"<<K<<",\"seed\":"<<seed<<",\"triangle\":"<<triangle<<",\"q\":"<<q<<",\"gprob\":"<<gprob
        <<",\"baseline\":"<<baseline<<",\"baseline_lo\":"<<baseline_lo<<",\"baseline_hi\":"<<baseline_hi<<",\"best\":"<<best<<",\"best_lo\":"<<ev.g_lo<<",\"best_hi\":"<<ev.g_hi
        <<",\"iterations\":"<<completed<<",\"accepted\":"<<accepted<<",\"elapsed\":"<<now_sec()-start<<",\"colors\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<full_color[k];std::cout<<"],\"opaque\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<best_design.op[k];std::cout<<"],\"black\":[";
    for(int k=0;k<K;k++)std::cout<<(k?",":"")<<best_design.bk[k];std::cout<<"]}\n";
}
'''
(root/"module.cpp").write_text(source)
