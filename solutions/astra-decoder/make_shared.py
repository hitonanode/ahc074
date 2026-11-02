from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'joint-detail.cpp').read_text()
s=s.replace('struct AtomicGateSearch {','std::vector<std::pair<int,int>> decoder_matching_check;\n\nstruct AtomicGateSearch {')
s=s.replace('''            double cost=e.fixed+c.exact_goal_mean(x)+c.exact_goal_mean(y);''','''            // Match Design::initialize's float gcost storage, operation order,
            // sort comparator, and ascending partner lists exactly.
            const float gc=float(0.5*(c.exact_goal_mean(x)+c.exact_goal_mean(y)));
            double cost=.65*__builtin_popcountll(e.d>>c.G)+2*gc+.04*__builtin_popcountll(e.d);''')
s=s.replace('''return a.price<b.price||(a.price==b.price&&a.i<b.i);''','''return a.price<b.price;''')
s=s.replace('''            for(auto e:es){auto&p=pairs[e.i];partners[p.u].push_back({p.v,e.i});partners[p.v].push_back({p.u,e.i});}''','''            for(int i=0;i<int(pairs.size());i++)if(result.prices[i]>=0){auto&p=pairs[i];partners[p.u].push_back({p.v,i});partners[p.v].push_back({p.u,i});}''')
s=s.replace('''        int nonlinear=0;for(int j=0;j<c.G;j++)''','''        const auto final_matching=evaluate(gm);
        decoder_matching_check.clear();
        for(int i:final_matching.selected){auto&e=pairs[i];decoder_matching_check.emplace_back(e.u,e.v);}
        std::sort(decoder_matching_check.begin(),decoder_matching_check.end());
        std::cerr << "decoder_final_exact_obj = " << final_matching.value << '\\n';
        int nonlinear=0;for(int j=0;j<c.G;j++)''')
a='''        if (des->initialize(compatible2, estimate2,
                            [&]() { return !untimed && elapsed_sec() > kInitExpiry; }))
            break;'''
b='''        if (des->initialize(compatible2, estimate2,
                            [&]() { return !untimed && elapsed_sec() > kInitExpiry; })) {
            if(!decoder_matching_check.empty()) {
                std::vector<std::pair<int,int>> actual;
                for(auto u:des->unit)if(u.b>=0)actual.emplace_back(std::min(u.a,u.b),std::max(u.a,u.b));
                std::sort(actual.begin(),actual.end());
                std::cerr << "decoder_matching_equal = " << (actual==decoder_matching_check) << '\\n';
                assert(actual==decoder_matching_check);
            }
            break;
        }'''
assert a in s;s=s.replace(a,b)
(p/'shared.cpp').write_text(s)
