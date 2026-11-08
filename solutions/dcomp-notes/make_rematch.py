"""Exact memoization of repeated probability polynomials in native rematching."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
base=(ROOT/'solutions/dcomp-climb-cache/main.cpp').read_text()
def sub(s,a,b):
 assert s.count(a)==1,(s.count(a),a[:80]);return s.replace(a,b)
s=sub(base,'''    static double range_gain(u64 target,u64 donor,u64 range,int c,const double* p) {''','''    // Probabilities are fixed until the next rebuild. The complete target ID
    // matters: its rounded prefix differences need not equal another target's.
    struct GainMemo { u64 key=~u64(0); double value=0; };
    mutable std::vector<GainMemo> gain_memo=std::vector<GainMemo>(1U<<12);
    unsigned gain_epoch=0;
    double range_gain(int t,u64 target,u64 donor,u64 range,int c,const double* p) const {''')
s=sub(s,'''        return Design::covered_gain(covered,[&](int j){return p[j];});''','''        if(!covered)return 0;
        if(d.H>40 || gain_epoch>=65536)return Design::covered_gain(covered,[&](int j){return p[j];});
        const u64 key=(u64(gain_epoch)<<48)|(covered<<8)|unsigned(t);
        auto& memo=gain_memo[(key*0x9E3779B97F4A7C15ULL)>>(64-12)];
        if(memo.key==key)return memo.value;
        const double value=Design::covered_gain(covered,[&](int j){return p[j];});
        memo.key=key;memo.value=value;return value;''')
s=sub(s,'''    void update_probability() {
        if (extra) {''','''    void update_probability() {
        ++gain_epoch;
        if (extra) {''')
s=s.replace('range_gain(d.hb[t],','range_gain(t,d.hb[t],')
p=ROOT/'solutions/dcomp-rematch-memo';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-climb-cache（その元はlegal-tie-fast）

rematch の target/donor 評価で同じ確率多項式を繰り返す部分だけ、4096スロットに保存する。キーは確率を更新するたびの世代、target番号、覆う穴の完全なビットマスク。衝突は完全キーで判定する。通常より大きい40列超の実験設定では元の式を計算する。元の浮動小数点演算と加算順序を保つ。

探索の反復数、候補、乱数、受理規則、注文処理は変えない。時間不足の切替なし。ログ・実験スイッチ・プロファイラを保持する。
''')
