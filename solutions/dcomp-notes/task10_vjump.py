from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-stack-b/main.cpp').read_text()
a=s.index('            for(int c=0;c<s.H;++c) {\n                dp[c+1]=dp[c];');b=s.index('            U64 covered=0;int nf=0,digs=0,length=0;',a)
old=s[a:b]
new=old
x='''                    int saving=std::popcount(cov&wrong);
                    for(int lo=d.start[t][k];lo<=c;++lo) {'''
y='''                    const U64 covered_wrong=cov&wrong;
                    int saving=std::popcount(covered_wrong);
                    for(int lo=d.start[t][k];lo<=c;) {'''
assert new.count(x)==1;new=new.replace(x,y)
x='''                        saving-=int(((cov&wrong)>>lo)&1);
                        if(saving<=price+depth)break;'''
y='''                        // Between two strict rises of dp[lo], the prefix value is
                        // constant and saving can only decrease. Such a position can
                        // never beat the earlier tested one; retain its original tie.
                        const U64 next=rises&~low(lo+1);
                        if(!next)break;
                        const int after=std::countr_zero(next);
                        saving-=std::popcount(covered_wrong&(low(after)^low(lo)));
                        if(saving<=price+depth)break;
                        lo=after;'''
assert new.count(x)==1;new=new.replace(x,y)
# rises records dp[i]>dp[i-1], and only existing i<=c may be used by column c.
new='            U64 rises=0;\n'+new
needle='''                }
            }
''';assert new.endswith(needle);new=new[:-len(needle)]+'''                }
                if(dp[c+1]>dp[c])rises|=U64(1)<<(c+1);
            }
'''
ref=old
import re
for name in ['dp','prev','picked','pickdepth']:ref=re.sub(r'\b'+name+r'\b','ref_'+name,ref)
check='''#ifdef VJUMP_CHECK
            {
                std::array<double,MaxH+1> ref_dp{};
                std::array<int,MaxH+1> ref_prev{},ref_picked{},ref_pickdepth{};
                ref_picked.fill(-1);
'''+ref+'''                for(int i=0;i<=s.H;++i)if(std::bit_cast<U64>(dp[i])!=std::bit_cast<U64>(ref_dp[i]) ||
                    prev[i]!=ref_prev[i] || picked[i]!=ref_picked[i] || pickdepth[i]!=ref_pickdepth[i]) {
                    std::cerr<<"VJUMP_MISMATCH "<<t<<' '<<sample<<' '<<i<<'\\n';std::abort();
                }
            }
#endif
'''
s=s[:a]+new+check+s[b:]
for check in [False,True]:
 p=r/'solutions'/('dcomp-vjump'+('-check' if check else ''));assert not p.exists();p.mkdir();(p/'main.cpp').write_text(('#define VJUMP_CHECK\n' if check else '')+s)
 (p/'README.md').write_text('改良元: solutions/dcomp-stack-b\n\nVのcover期待値のDPで、先頭費用dp[lo]が厳密に増える位置だけを次の候補にする。dpが同じ区間ではsavingは減る一方なので最初の位置に勝てない。最初のlo、元の同点選択、gainのdouble演算は維持し、飛ばした区間のwrong bit数だけ整数savingから引く。検証版は全sampleで旧DPを再計算し、各dpのdouble bitとprev/picked/depthを照合する。\n\n設計候補・Vの式・注文予算・乱数は不変。固定予算、ログ・実験スイッチ・DesignStoreを維持、時間fallbackなし。\n')
