from pathlib import Path
import re
root=Path(__file__).parent
source=(root/'main.cpp').read_text()
a=source.index('struct Design {');b=source.index('\nstruct Paper {',a)
s=re.sub(r'\bDesign\b','MixedDesign',source[a:b])
s=s.replace('    static constexpr double reset_strength = 2.0;','    static constexpr double reset_strength = 2.0;\n    int own0=-1,own1=-1;\n    std::array<double,P> single_cost{};\n    bool mixed()const{return own0>=0;}')
s=s.replace('    bool valid(const Unit& u, int c) const { return u.b < 0 || (((hb[u.a] ^ hb[u.b]) >> c) & 1) == 0; }','    bool valid(const Unit& u, int c) const { return !invalid_bit(u,c); }')
s=s.replace('    int invalid_bit(const Unit& u, int c) const {','''    int invalid_bit(const Unit& u, int c) const {
        if(mixed()){
            bool own=u.a==own0||u.a==own1||u.b==own0||u.b==own1;
            if(own)return u.b>=0||c!=0;
            if(c==0)return 1;
        }''')
s=s.replace('    double hcost(int j) const {','    double hcost(int j) const {\n        if(mixed()&&j==0)return 0;')
s=s.replace('return u.b < 0 ? 0 : gcost[u.a][u.b] * 2;', 'return u.b < 0 ? single_cost[u.a] : gcost[u.a][u.b] * 2;')
s=s.replace('                if (!compatible(A[a], A[b])) continue;','                if (mixed()&&(a==own0||a==own1||b==own0||b==own1))continue;\n                if (!compatible(A[a], A[b])) continue;')
s=s.replace('hq[L] = {}, reset[L] = {};','hq[L] = {}, reset[L] = {}, hole_weight[L] = {};')
s=s.replace('Q[r] = _mm256_div_ps(numerator,s);','Q[r] = _mm256_mul_ps(_mm256_div_ps(numerator,s),_mm256_load_ps(hole_weight+8*r));')
s=s.replace('for(int j=0;j<H;j++){reset[j]=D.reset_targets[j];', 'for(int j=0;j<L;j++)hole_weight[j]=D.mixed()&&j==0?0:1;\n            for(int j=0;j<H;j++){reset[j]=D.reset_targets[j];')
s=s.replace('hq[j]=qf(n0[j],n1[j],reset[j]);','hq[j]=qf(n0[j],n1[j],reset[j])*hole_weight[j];')
s=s.replace('        ANNEAL_TARGET void handle_swap(int a, int b) {','        ANNEAL_TARGET void handle_swap(int a, int b) {\n            if(D.mixed()&&(a==0||b==0))return;')
s=s.replace('        ANNEAL_TARGET void column_swap(int a, int b) {','        ANNEAL_TARGET void column_swap(int a, int b) {\n            if(D.mixed()&&(a==0||b==0))return;')
s=s.replace('        ANNEAL_TARGET void multi_move(int k, const int* xs, const Unit* nu) {','        ANNEAL_TARGET void multi_move(int k, const int* xs, const Unit* nu) {\n            for(int i=0;i<k;i++)if(D.invalid_bit(nu[i],nu[i].c))return;')
# Reserve the two actual decoder commodities through every code path.
s=s.replace('if((it&4095)==0){MixedDesign check=D;', 'if((it&4095)==0){for(auto u:D.unit)assert(D.valid(u,u.c));MixedDesign check=D;')
root.joinpath('design.hpp').write_text(s)
