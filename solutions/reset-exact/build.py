from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'perforated-eight/main.cpp').read_text()
s=s.replace('    struct Unit {\n        int a = -1, b = -1, c = -1;','    static inline bool dynamic_reset=true;\n    struct Unit {\n        int a = -1, b = -1, c = -1;',1)
s=s.replace('static constexpr int kAnnealSegments = 4;','static inline int kAnnealSegments = 4;')
s=s.replace('    void update(const Unit& u, int sgn) {\n        cur -= cval[u.c];','    void update(const Unit& u, int sgn) {\n        if(dynamic_reset)cur-=hcost(u.c);\n        cur -= cval[u.c];')
s=s.replace('        nt[u.c] += sgn * weight(u);','        nt[u.c] += sgn * weight(u);\n        if(dynamic_reset){reset_targets[u.c]=float(reset_strength*nt[u.c]);cur+=hcost(u.c);}',1)
s=s.replace('    void rebuild() {\n        std::fill(nc.begin()', '    void rebuild() {\n        if(dynamic_reset)std::fill(reset_targets.begin(),reset_targets.end(),0);\n        std::fill(nc.begin()',1)
# Only three neighborhoods change the number of targets in a column.
for name,end,prepare,undo in [
 ('column_move','target_move','if(D.dynamic_reset){reset[P]+=D.reset_strength*dnt[0];reset[Q]+=D.reset_strength*dnt[1];}','if(D.dynamic_reset){reset[P]-=D.reset_strength*dnt[0];reset[Q]-=D.reset_strength*dnt[1];}'),
 ('column_swap','multi_move','if(D.dynamic_reset)std::swap(reset[a],reset[b]);','if(D.dynamic_reset)std::swap(reset[a],reset[b]);'),
 ('multi_move','run','if(D.dynamic_reset)for(int i=0;i<ncols;i++)reset[cols[i]]+=D.reset_strength*dnt[i];','if(D.dynamic_reset)for(int i=0;i<ncols;i++)reset[cols[i]]-=D.reset_strength*dnt[i];'),
]:
 a=s.index('        ANNEAL_TARGET void '+name+'(');b=s.index('        ANNEAL_TARGET void '+end+'(',a)
 piece=s[a:b]
 needle='            const float dq = eval_holes(d0, d1, N0, N1, Qv);'
 assert piece.count(needle)==1
 piece=piece.replace(needle,'            '+prepare+'\n'+needle)
 needle='            if (!accept(delta)) return;'
 assert piece.count(needle)==1
 piece=piece.replace(needle,'            if (!accept(delta)) {'+undo+'return;}')
 s=s[:a]+piece+s[b:]
(p/'main.cpp').write_text(s)
