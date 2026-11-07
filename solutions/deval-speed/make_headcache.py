from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/deval-fast/main.cpp').read_text()
a=s.index('struct ProbabilityHead {');b=s.index('// Reassign mobile targets',a);v=s[a:b]
v=v.replace('    double strength;','''    std::array<u64,P> target_holes{},unit_cover{},unit_bits{};
    std::array<int,P> target_column{},unit_column{};
    // All masks are rebuilt together with the probabilities after a proposed cycle.
    // The floating-point polynomial and its enumeration order stay unchanged.
    static double range_gain(u64 target,u64 donor,u64 range,int c,const double* p) {
        const u64 mismatch=(target^donor)&range;
        const int level=mismatch?64-__builtin_clzll(mismatch):0;
        if(level>=c)return 0;
        const u64 covered=range&low_bits(c)&~low_bits(level);
        return Design::covered_gain(covered,[&](int j){return p[j];});
    }
    double strength;''',1)
start=v.index('    double donor(');end=v.index('    // The filler value that the heads',start)
v=v[:start]+'''    double donor(const Design::Unit& u,int slot=-1) const {
        AF_SCOPE(head_donor,64);
        double sum=0;
        const u64 dy=(u.b>=0?d.hb[u.a]^d.hb[u.b]:0)|extra_holes(slot);
        const u64 cover=low_bits(u.c+1)&~dy,bits=d.hb[u.a];
        for(int t=0;t<P;++t)if(target_column[t]!=u.c)
            sum+=range_gain(d.hb[t],bits,cover&target_holes[t],u.c,q[t].data());
        return sum;
    }
'''+v[end:]
start=v.index('    double target(');end=v.index('    // Recomputes everything',start)
v=v[:start]+'''    double target(int t,const Design::Unit& u,int slot=-1) const {
        AF_SCOPE(head_target,256);
        double sum=0;
        const u64 dx=(u.b>=0?d.hb[u.a]^d.hb[u.b]:0)|extra_holes(slot);
        const u64 holes=~low_bits(u.c+1)|dx;
        for(int y:active_heads)if(unit_column[y]!=u.c)
            sum+=beta[y]*range_gain(d.hb[t],unit_bits[y],unit_cover[y]&holes,unit_column[y],q[t].data());
        return sum;
    }
'''+v[end:]
needle='''            diff[x] = (u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0) | extra_holes(x);
        }'''
replace='''            diff[x] = (u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0) | extra_holes(x);
            unit_cover[x]=low_bits(u.c+1)&~diff[x];unit_bits[x]=d.hb[u.a];unit_column[x]=u.c;
        }
        for(int t=0;t<P;++t) {
            const int x=d.owner[t];target_column[t]=d.unit[x].c;
            target_holes[t]=~low_bits(target_column[t]+1)|diff[x];
        }'''
assert needle in v;v=v.replace(needle,replace,1)
s=s[:a]+v+s[b:]
d=R/'solutions/deval-headcache';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-headcache

改良元: solutions/deval-fast。

仕上げのProbabilityHeadで、各対象の穴マスク、各供給紙の被覆マスクと色と列をrebuild時に一度計算する。Hungarianの費用行列と候補巡回の評価で繰り返していた整数の参照・シフトを省く。再割当てで状態が変われば従来と同じrebuildで全項を更新する。確率多項式と浮動小数点の列挙順は同じ。同じ列の寄与は元から正の0で、省略しても非負の和は変わらない。

探索予算・固定乱数・紙の設計状態は同じ。時間不足による探索削減はない。
''')
print(len(s.encode()))
