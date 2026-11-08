"""Reuse exact initial prefix coverage in both post-processing replays."""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def replace(s,a,b):
    assert s.count(a)==1,(s.count(a),a[:100]);return s.replace(a,b)
s=replace(B,'        bool masks_exact = false;  // every paper\'s black windows are opaque',
          '        std::array<u64,K+1> initial_cover{};\n        bool masks_exact = false;  // every paper\'s black windows are opaque')
s=replace(s,'            c.blocks[0][j] = {paper[k].opaque, paper[k].black};',
          '            c.blocks[0][j] = {paper[k].opaque, paper[k].black};\n            c.initial_cover[j+1]=c.initial_cover[j]|paper[k].opaque;')
s=replace(s,'            std::array<u64,K+1> cov;cov[0]=0;int valid=0;\n            auto visible=[&](int k,int p) {\n                for(;valid<p;++valid)cov[valid+1]=cov[valid]|paper[o[valid]].opaque;\n                return paper[k].opaque&~cov[p];\n            };',
'''            std::array<u64,K+1> cov;int valid=K,unchanged=K;
            auto truncate=[&](int pos){valid=std::min(valid,pos);unchanged=std::min(unchanged,pos);};
            auto visible=[&](int k,int p) {
                // Before the first changed position, the original prefix is still exact.
                if(p<=unchanged)return paper[k].opaque&~post_context.initial_cover[p];
                if(valid==unchanged)cov[valid]=post_context.initial_cover[valid];
                for(;valid<p;++valid)cov[valid+1]=cov[valid]|paper[o[valid]].opaque;
                return paper[k].opaque&~cov[p];
            };''')
# These two lines occur only inside the commuting screen replay.
old='shift_byte(o,p,d);valid=std::min(valid,std::min(p,d));';assert s.count(old)==2
s=s.replace(old,'shift_byte(o,p,d);truncate(std::min(p,d));')
s=replace(s,'            shift_byte(o,kp,K-1);valid=0;',
          '            shift_byte(o,kp,K-1);truncate(kp);')
screen=s
s=replace(s,'        std::vector<int> lengths;\n        Moves path;',
          '        std::vector<int> lengths;\n        std::vector<int> unchanged;  // minimum position touched in the cached prefix\n        Moves path;')
s=replace(s,'                prefix.lengths.resize(input_ops.size() + 3);',
          '                prefix.lengths.resize(input_ops.size() + 3);\n                prefix.unchanged.resize(input_ops.size()+3);')
s=replace(s,'            prefix.lengths[0] = 0;',
          '            prefix.lengths[0] = 0;\n            prefix.unchanged[0]=K;')
s=replace(s,'                int cover_valid = 0;\n                cover[0] = 0;',
          '                int cover_valid=K,unchanged=K;')
s=replace(s,'                    ord = prefix.orders[common];',
          '                    ord = prefix.orders[common];\n                    unchanged=cover_valid=prefix.unchanged[common];')
s=replace(s,'                        prefix.lengths.resize(trial.size() + 1);',
          '                        prefix.lengths.resize(trial.size() + 1);\n                        prefix.unchanged.resize(trial.size()+1);')
s=replace(s,'''                        for (; cover_valid < p; cover_valid++)
                            cover[cover_valid + 1] = cover[cover_valid] | paper[ord[cover_valid]].opaque;
                        if (!(paper[k].opaque & ~cover[p])) { remember(index); return false; }''',
'''                        u64 mask;
                        if(p<=unchanged)mask=post_context.initial_cover[p];
                        else {
                            if(cover_valid==unchanged)cover[cover_valid]=post_context.initial_cover[cover_valid];
                            for(;cover_valid<p;++cover_valid)
                                cover[cover_valid+1]=cover[cover_valid]|paper[ord[cover_valid]].opaque;
                            mask=cover[p];
                        }
                        if (!(paper[k].opaque & ~mask)) { remember(index); return false; }''')
s=replace(s,'                        cover_valid = std::min(cover_valid, std::min(p, dest));\n                        path.push_back({k, dest});',
          '                        cover_valid = std::min(cover_valid, std::min(p, dest));\n                        unchanged=std::min(unchanged,std::min(p,dest));\n                        path.push_back({k, dest});')
s=replace(s,'                        prefix.lengths[index + 1] = path.size();',
          '                        prefix.lengths[index + 1] = path.size();\n                        prefix.unchanged[index+1]=unchanged;')
for name,source,desc in [('dcomp-t11-cover-screen',screen,'可換anchor群の再生で、最初の変更位置より上は初期prefixの被覆を使う。紙kを除いたときも、その位置より上の被覆を捨てない。'),
                         ('dcomp-t11-cover-all',s,'可換anchor群と通常のprefix replayの両方で、初期prefixの被覆を使う。キャッシュした各操作prefixに最小変更位置を保存する。')]:
    d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
    (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'演算はu64のORのみで、元の可視性と操作列を保つ。\n\n要求予算、設計9候補、実験スイッチ、ログ、目次・段の目印、DesignStoreを維持。時計による予算変更はない。\n')
