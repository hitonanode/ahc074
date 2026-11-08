from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text();s=B
a='    std::array<NextPaper, K> next_paper;';assert s.count(a)==1;s=s.replace(a,a+'\n    std::array<uint8_t,64> next_colors{};')
a='            next_paper[k] = {uint16_t(k * stride), uint8_t(column_color[k]), uint8_t(colmdp_type[k])};';assert s.count(a)==1
s=s.replace(a,a+'\n            if(column_color[k]>=0)next_colors[column_color[k]>>1]|=uint8_t(1U<<(column_color[k]&1));')
a='''                do {
                    const auto& np=next_paper[key[i]];
                    if(first[np.color]<0)first[np.color]=depth;
                    cost+=depth_terms[np.offset+depth];++depth;
                    if(mdp_scan)code=(code<<2)|np.type;
                    ++i;
                } while(i<end && (next_paper[key[i]].color>>1)==c);''';assert s.count(a)==1
s=s.replace(a,'''                int seen=int(first[2*c]>=0)+2*int(first[2*c+1]>=0);
                // Once every color printed in this column has a first paper,
                // no later paper can change first[]. The running double and
                // MDP code still consume all papers in exactly the same order.
                while((seen&next_colors[c])!=next_colors[c]) {
                    const auto& np=next_paper[key[i]];
                    if(first[np.color]<0){first[np.color]=depth;seen|=1<<(np.color&1);}
                    cost+=depth_terms[np.offset+depth];++depth;
                    if(mdp_scan)code=(code<<2)|np.type;
                    ++i;
                    if(i==end || (next_paper[key[i]].color>>1)!=c)break;
                }
                while(i<end && (next_paper[key[i]].color>>1)==c) {
                    const auto& np=next_paper[key[i]];
                    cost+=depth_terms[np.offset+depth];++depth;
                    if(mdp_scan)code=(code<<2)|np.type;
                    ++i;
                }''')
for name,source,extra in [('dcomp-t11-nextcolors',s,''),('dcomp-t11-nextcolors-check','#define NEXT_PREFIX_CHECK 1\n'+s,'全next_costを旧関数でも計算しdouble全bitを照合する検証版。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\nnext_costの列内scanで、その列に印刷される全ての色の最初の深さが既に分かったら、残りの紙でfirst配列を検査しない。各紙の費用加算とMDP符号化は順番も回数も元と同じ。色が列から全て取り出されている場合は旧検査を最後まで行う。'+extra+'\n\nprofileの列内scanを対象にする。近似・fast-math・時計分岐は使わない。予算、ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
