# 穴費用の除算を保つ範囲

実験の対象は `eval_holes` の単精度除算だけ。既定の丸めはnearest-even。fast-mathは使わない。

穴数a,bは非負整数、a+b≤256。reset=2nt、nt≤256なので、分子n=ab+nt min(a,b)は0–49152の整数、分母d=max(1,a+b+2nt)は1–768の整数になる。これらの加算・乗算・FMAは整数として正確。

RCPPSの相対誤差上限は1.5×2^-12である。[Intel SDM Volume 2](https://cdrdv2-public.intel.com/774492/325383-sdm-vol-2abcd.pdf)。以下はこの上限からの導出。

u=2^-24とする。逆数seed r0を `r=fma(r0, fma(-d,r0,1), r0)` で補正すると、相対誤差は4u未満。`q=RN(nr)` の相対誤差は6u未満。残差 `e=fma(-q,d,n)` を使い `fma(r,e,q)` とすると、最後の丸め直前の値と正確なn/dの相対差は32u²未満になる（残差の丸め誤差も含む）。

正のn≤65536とd≤768では、n/dは隣接floatの中点そのものにならない。中点を既約分数にした分子は少なくとも2^24+1であるため。中点までの相対距離は保守的に1/(d×2^26)以上で、最悪でも1.94×10^-11。上の補正誤差32u²<1.14×10^-13より大きいので、最後のnearest-even丸めは通常の単精度除算と一致する。n=0はどちらも+0。

`../deval-lastlab/verify_quotient.cpp` はn=0–65536、d=1–768の50,332,416組を元のSIMD除算とbit単位で比較する。GCC/Clangの実行結果は `../deval-lastlab/quotient-verification.json`。解法全体の出力と速度は別に標準評価runnerで検査する。
