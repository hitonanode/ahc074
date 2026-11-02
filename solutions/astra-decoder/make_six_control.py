from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'seven.cpp').read_text()
a=s.index('WindowStats assign_windows(std::vector<u64>& A,int m,int g,');b=s.index('// kBitLanes[v][i]',a)
f=s[a:b]
f=f.replace('assert(m==7&&g>=21&&g<64);','assert((m==6||m==7)&&g>=m*(m-1)/2&&g<64);\n    const int ne=m*(m-1)/2;')
f=f.replace('auto& costs=Poset7Costs::get();','''struct Costs {
        int m;long long misses=0;
        int cost(u64 raw){
            if(m==7)return Poset7Costs::get().cost(raw);
            u64 closed=closure8(raw,6);if(closed&kDiagonal)return 0;
            return 1+7*PosetSums::get().both_of(closed);
        }
    } costs{m};''')
f=f.replace('constexpr int need=72;', 'const int need=256-(191-m);')
f=f.replace('a<7;a++','a<m;a++').replace('b<7;b++','b<m;b++')
f=f.replace('e<21','e<ne').replace('ee<21','ee<ne')
f=f.replace('closure8(rr,7)','closure8(rr,m)').replace('closure8(r,7)','closure8(r,m)')
s=s[:a]+f+s[b:]
s=s.replace('kCapPaper = 7','kCapPaper = 6').replace('int M = 7, G = 38;  // Seven generic sheets plus the fixed cap.','int M = 6, G = 38;  // Control: six sheets with the unpacked assignment engine.')
s=s.replace('static constexpr int GM = 7;', 'static constexpr int GM = 6;')
s=s.replace('return (Poset7Costs::get().cost(r) - 1) / 10080.0;', 'return PosetSums::get().both_of(r) / 1440.0;')
(p/'six-control.cpp').write_text(s)
