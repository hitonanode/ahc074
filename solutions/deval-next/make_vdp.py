from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/deval-seven-wide/main.cpp').read_text();a=base.index('__attribute__((target("popcnt"))) inline CoverResult expectation');b=base.index('\n} // namespace deval',a)
s=base[a:b]
s=s.replace('    CoverResult ans;','    assert(price==1.6); // This frozen V uses only the 8/5 placement price.\n    CoverResult ans;',1)
s=s.replace('''            std::array<double,MaxH+1> dp{};''','''            std::array<double,MaxH+1> dp{};
            std::array<int,MaxH+1> score{};''',1)
s=s.replace('''                dp[c+1]=dp[c];''','''                dp[c+1]=dp[c];score[c+1]=score[c];''',1)
old='''                        const double gain=saving-price-depth;
                        if(gain>0&&dp[lo]+gain>dp[c+1]+1.e-12) {
                            dp[c+1]=dp[lo]+gain;prev[c+1]=lo;picked[c+1]=k;pickdepth[c+1]=depth;
                        }'''
new='''                        const int gain5=5*saving-8-5*depth;
                        if(gain5>0&&score[lo]+gain5>score[c+1]) {
                            score[c+1]=score[lo]+gain5;
                            // Keep the original double arithmetic for the reported V features.
                            const double gain=saving-price-depth;
                            dp[c+1]=dp[lo]+gain;prev[c+1]=lo;picked[c+1]=k;pickdepth[c+1]=depth;
                        }'''
assert old in s;s=s.replace(old,new,1)
def put(name,x,desc):
 text=base[:a]+x+base[b:];p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(text);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n'+desc+'\n\nVの配置費用は元の固定値1.6のみを使う。候補と固定探索予算は共通で、時間による打切りはない。\n');print(name,len(text.encode()))
put('deval-vintdp',s,'Vの区間DPの大小比較を5倍の整数で行う。得は全て1/5単位で、同点の選び方を保つ。採用した経路のdouble加算は元の式と順序で行い、特徴量の値を保つ。')
s=s.replace('''            std::array<int,MaxH+1> score{};''','''            std::array<int,MaxH+1> score{},plateau{};''',1)
s=s.replace('''                dp[c+1]=dp[c];score[c+1]=score[c];''','''                dp[c+1]=dp[c];score[c+1]=score[c];plateau[c+1]=plateau[c];''',1)
a1=s.index('                    for(int lo=d.start[t][k];lo<=c;++lo) {');b1=s.index('                }\n            }\n            U64 covered',a1)
loop='''                    for(int start=d.start[t][k];start<=c;) {
                        const int gain5=5*saving-8-5*depth;
                        if(gain5<=0)break;
                        const U64 rest=cov&wrong&~low(start);
                        const int end=rest?int(std::countr_zero(rest)):c;
                        // dp is nondecreasing. Within one constant-saving interval,
                        // retain the earliest start attaining its last DP value.
                        const int lo=std::max(start,plateau[end]);
                        if(score[lo]+gain5>score[c+1]) {
                            score[c+1]=score[lo]+gain5;
                            const double gain=saving-price-depth;
                            dp[c+1]=dp[lo]+gain;prev[c+1]=lo;picked[c+1]=k;pickdepth[c+1]=depth;
                        }
                        saving-=int(((cov&wrong)>>end)&1);
                        start=end+1;
                    }
'''
s=s[:a1]+loop+s[b1:]
s=s.replace('''                }
            }
            U64 covered''','''                }
                if(score[c+1]>score[c])plateau[c+1]=c+1;
            }
            U64 covered''',1)
put('deval-vskipdp',s,'Vの区間DPを整数で比較し、同じ修復数になる開始位置の区間をまとめる。DPが最大になる最初の開始位置を選ぶことで、元の同点処理とdouble加算を保つ。')
