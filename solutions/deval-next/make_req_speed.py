from pathlib import Path
R=Path(__file__).resolve().parents[2];b=(R/'solutions/deval-seven-wide/main.cpp').read_text()
def put(name,s,desc):
 p=R/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n'+desc+'\n\n予算と候補順は基準と同じ。整数の必要条件の検査順または重複計算だけを変える。時間による打切りはない。\n');print(name,len(s.encode()))
a='''                for (int k = next[root]; k != root && k != kCapPaper; k = next[k])
                    if (k < M) return false;
'''
c='''                if (view != A[u]) return false;
'''
s=b.replace(a,'',1).replace(c,c+a,1)
put('deval-cap-late',s,'注文後処理で、完成表示が正しい候補だけについてcapより上に汎用紙がないか調べる。')
a2='''                for (int j = 0, cap = find_paper(ord, kCapPaper); j < cap; j++)
                    if (ord[j] < M) return false;'''
assert a2 in s
put('deval-cap-once',s.replace(a2,'                // The final linked order has already passed the cap invariant.',1),'cap不変条件を完成表示の検査後に一度だけ確認する。同じ最終順序に到達する合法性リプレイ後の重複検査を省く。')
# Hoist paper/target colors which do not vary with a deletion pair.
s=b
needle='''        auto& trial = eject_trial;'''
s=s.replace(needle,'''        std::array<u64,K> candidate_wrong, candidate_right;
        for(int ci=0;ci<candidate_count;++ci){
            int k=candidates[ci];candidate_wrong[ci]=paper[k].opaque&(paper[k].black^A[u]);
            candidate_right[ci]=paper[k].opaque&~candidate_wrong[ci];
        }
'''+needle,1)
old='''                    u64 wrong = paper[k].opaque & (paper[k].black ^ A[u]);
                    if (!bad || (bad & ~paper[k].opaque) || (bad & wrong)) continue;'''
assert old in s
s=s.replace(old,'''                    const u64 wrong = candidate_wrong[ci];
                    if (!bad || (bad & ~candidate_right[ci])) continue;''',1)
put('deval-eject-right',s,'2削除1修復の後処理で、注文に対して各修復候補が正しい窓の集合を先に作る。削除する操作の組によらない計算を外側へ移す。')
