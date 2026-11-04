from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'as6-canon/main.cpp').read_text();s=s[:s.index('struct Paper {')]
a=s.index('struct Design {');pre=s[:a];s=s[a:]
s=s.replace('int M, G, H, U, need;', 'int active;int M, G, H, U, need;')
s=s.replace('Design(const std::vector<u64>& a, int m, int g) : M(m), G(g), H(63 - g), U(191 - m), need(256 - U), A(a)', 'Design(const std::vector<u64>& a, int m, int g,int active_count=256) : active(active_count), M(m), G(g), H(63 - g), U(191 - m), need(active_count - U), A(a)')
s=s.replace('for (const auto& u : unit) update(u, 1);', 'for(int t=active;t<256;t++)for(int j=0;j<H;j++)hn[j][hb[t]>>j&1]++;\n        for(int j=0;j<H;j++)cur+=hcost(j);\n        for (const auto& u : unit) update(u, 1);')
x=s.index('    bool initialize(');y=s.index('    // Annealing of the pairing',x)
init=s[x:y].replace('a < 256','a < active').replace('b < 256','b < active')
s=s[:x]+init+s[y:]
s=s.replace('auto tcol = [&](int t) { return unit[owner[t]].c; };', 'auto tcol = [&](int t) { return owner[t]<0?-1:unit[owner[t]].c; };')
(p/'design.hpp').write_text(pre+s+'\n} // namespace\n')
