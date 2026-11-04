from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'group-lab/design.cpp').read_text()
s=s[s.index('struct Group {'):s.index('int main(int argc')]
s=s.replace(',27>',',63>').replace('assert(H<=27);','assert(H<=63);')
s=s.replace('return .15*total*(n-1)*.5+.85*best;','return best;')
s=s.replace('std::popcount(d)<=42','std::popcount(d)<=40')
s=s.replace('    static double holecost(std::array<int,2> a){return a[0]+a[1]?1.6*a[0]*a[1]/(a[0]+a[1]):0;}',
'''    std::array<double,63>reset{};
    double holecost(int c)const{double x=holes[c][0],y=holes[c][1],t=reset[c];return 1.6*(x*y+.5*t*std::min(x,y))/std::max(1.,x+y+t);}
    void refresh(){for(int c=0;c<H;c++){reset[c]=0;for(int w=1;w<=3;w++)reset[c]+=2*w*(counts[c][w][0]+counts[c][w][1]);}rebuild();}''')
s=s.replace('holecost(holes[j])','holecost(j)')
s=s.replace('''        for(int it=0;it<iterations;it++){
            const double temp''','''        for(int it=0;it<iterations;it++){
            if(it%std::max(1,iterations/4)==0){refresh();best=current;best_units=units;best_handles=handles;}
            const double temp''')
(p/'model.cpp').write_text((p/'model_prefix.hpp').read_text()+s+(p/'model_main.inc').read_text())
