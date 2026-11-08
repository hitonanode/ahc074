from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def repl(s,a,b,n=1):assert s.count(a)==n,(a[:80],s.count(a));return s.replace(a,b)
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n固定探索予算、既存ログ・実験スイッチ・profiler・目次と段、DesignStoreは保持。時計による分岐は追加しない。\n')
# Profile the residual post-exclusive block at its concrete suboperations.
s=B
s=repl(s,'CfProfile cf_post{"post"};','CfProfile cf_post{"post"};\nCfProfile cf_anchorize{"anchorize"},cf_anchor_candidates{"anchor_candidates"},cf_screen_prepare{"screen_prepare"};')
a='    static std::vector<Edit> anchorize(';i=s.index(a);j=s.index('{',i)
s=s[:j+1]+'\n        CF_SCOPE(anchorize);'+s[j+1:]
s=repl(s,'        auto anchor_candidates = [&](int i) {','        auto anchor_candidates = [&](int i) {\n            CF_SCOPE(anchor_candidates);')
s=repl(s,'            auto& S = screen;\n            S.edit_source=', '            CF_SCOPE(screen_prepare);\n            auto& S = screen;\n            S.edit_source=')
# report() uses a list of pointers.
a='&cf_post,';assert s.count(a)==1;s=s.replace(a,a+' &cf_anchorize, &cf_anchor_candidates, &cf_screen_prepare,')
write('dcomp-t11-anchor-prof','#define COLFAST_PROFILE 1\n'+s,'要求postの排他時間に残ったanchorize・anchor候補生成・screen準備を分解する計測専用版。')
# inline fixed storage avoids all anchor-vector growth, preserving iteration order.
s=repl(B,'            std::vector<int> anchors{-1};','''            struct Anchors {
                std::array<int,K+1> data;int size=0;
                void push_back(int a){data[size++]=a;}
                const int* begin()const{return data.data();}
                const int* end()const{return data.data()+size;}
            } anchors;
            anchors.push_back(-1);''')
write('dcomp-t11-anchor-array',s,'anchor候補の小さな動的vectorを固定容量の配列へ変更する。候補順と重複除去は同じ。戻り値はNRVOを使い、heap確保をなくす。')
# The edited source is frozen for each anchor scan, only the last accepted path is used.
s=repl(s,'                auto chosen = edits;','                bool anchor_improved=false;',2)
s=repl(s,'                    if (evaluate(trial)) chosen = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));','                    if (evaluate(trial)) anchor_improved=true;')
s=repl(s,'                                chosen = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));','                                anchor_improved=true;')
s=repl(s,'                edits = std::move(chosen);','                if(anchor_improved)edits=anchorize(initial_bytes,best_ops OP_TAG(,best_tags));',2)
write('dcomp-t11-anchor-lazy',s,'anchor候補を固定配列にする。さらに各anchor走査で途中の勝者を毎回anchorizeせず、最後に採られたbest_opsだけをanchorizeする。走査中のeditsは元から固定されており、試す候補と選択は変わらない。')
