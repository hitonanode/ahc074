"""Try valid column-and-handle permutations before each anneal branch."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vkick'
src=(HERE.parent/'deval-vreheat/main.cpp').read_text()
src=src.replace('env_real("DEVAL_REHEAT",4.)','env_real("DEVAL_REHEAT",2.)')
needle='        if(mode==1) {\n            des->anneal_reheat='
assert needle in src
src=src.replace(needle,'''        if(mode==1) {
            // A complete column keeps its own physical handle, so pair
            // compatibility and the availability of both colors are preserved.
            if(i)for(int step=0;step<int(env_real("DEVAL_KICKS",2));++step) {
                const int a=des->rng.below(des->H);
                const int distance=1+des->rng.below(int(env_real("DEVAL_KICK_DIST",6)));
                const int b=std::clamp(a+(des->rng.below(2)?distance:-distance),0,des->H-1);
                if(a==b)continue;
                std::swap(des->handle[a],des->handle[b]);
                for(auto& h:des->hb) {
                    const u64 z=((h>>a)^(h>>b))&1;h^=(z<<a)|(z<<b);
                }
                for(auto& u:des->unit)if(u.c==a||u.c==b)u.c^=a^b;
            }
            des->rebuild();des->refresh_reset();
            des->anneal_reheat=''')
assert len(src.encode())<520000
DEST.mkdir(exist_ok=True);(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vkick

改良元: `solutions/deval-vreheat`。

第2候補以降は、分岐直前に列全体と専用handleを一緒に2回入れ替え、別の局所解へ移るきっかけを作る。距離は1–6列。ペアの適合性と各列の両色を維持したまま、費用を再計算して通常の焼きなましで修復する。分岐温度の倍率は2。その他は親と同じ。

`DEVAL_KICKS` が入替回数、`DEVAL_KICK_DIST` が最大距離。再生成は `solutions/deval-vselect/make_kick.py`。
''')
print('source bytes',len(src.encode()))
