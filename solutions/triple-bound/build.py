from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'group-lab/design.cpp').read_text()
s=s[s.index('struct Group {'):s.index('int main(int argc')]
s=s.replace('for(int t=0;t<n;t++){Rows reach{};if(!p.extend(reach,p.A[a[t]],g.diff&p.gm))return;g.fee+=p.lower_cost(reach);}',
'''if(n==2){if(!p.compatible[a[0]][a[1]])return;g.fee=2*p.gcost[a[0]][a[1]];}
        if(n==3)g.fee=3*p.triple_price;''')
a=s.index('        for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(p.compatible[a][b])for(int c=b+1;')
b=s.index('\n    }',a)
s=s[:a]+'''        if(p.triple_price>=0)for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)for(int c=b+1;c<256;c++){
            U d=(p.A[a]^p.A[b])|(p.A[a]^p.A[c]);if(std::popcount(d)<=40)add({a,b,c},3);
        }'''+s[b:]
s=s.replace('return .15*total*(n-1)*.5+.85*best;','return best;')
s=s.replace('    static double holecost(std::array<int,2> a){return a[0]+a[1]?1.6*a[0]*a[1]/(a[0]+a[1]):0;}',
'''    std::array<double,27>reset{};
    double holecost(int c)const{double x=holes[c][0],y=holes[c][1],t=reset[c];return 1.6*(x*y+.5*t*std::min(x,y))/std::max(1.,x+y+t);}
    void refresh(){for(int c=0;c<H;c++){reset[c]=0;for(int w=1;w<=3;w++)reset[c]+=2*w*(counts[c][w][0]+counts[c][w][1]);}rebuild();}''')
s=s.replace('holecost(holes[j])','holecost(j)')
s=s.replace('''        for(int it=0;it<iterations;it++){
            const double temp''','''        for(int it=0;it<iterations;it++){
            if(it%std::max(1,iterations/4)==0){refresh();best=current;best_units=units;best_handles=handles;}
            const double temp''')
(p/'design.hpp').write_text('#include "common.hpp"\n#include <bit>\n#include <unordered_map>\nusing U=u64;\nstruct Problem {int M=6,G;U gm;std::vector<U>A;std::array<std::array<unsigned char,256>,256> compatible{};std::array<std::array<float,256>,256>gcost{};double triple_price;Problem(const Design&d,double price):G(d.G),gm(low_bits(d.G)),A(d.A),gcost(d.gcost),triple_price(price){for(int a=0;a<256;a++)for(int b=0;b<256;b++)compatible[a][b]=d.ok[a][b];}};\n'+s)
