"""Exact covered-gain cache: probabilities fixed until the explicit reset."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
parent=root/'solutions/deval-vbranch-o3'
dest=root/'solutions/deval-gaincache'
dest.mkdir(exist_ok=True)
s=(parent/'main.cpp').read_text()
pos=s.index('    // The expected saving of the paper of a unit')
s=s[:pos]+'''    // Exact memoization for one target and one covered mask. A probability
    // rebuild advances the generation; a miss uses the original arithmetic.
    struct GainMemo {
        struct Entry { u64 mask=0; unsigned generation=0; int target=-1; double value=0; };
        std::vector<Entry> entries = std::vector<Entry>(16384);
        unsigned generation=1;
        void reset() {
            if(++generation==0) { for(auto& e:entries)e.generation=0; generation=1; }
        }
        template<class Probability>
        double get(int target,u64 mask,Probability probability) {
            if(!mask)return 0;
            const u64 hash=(mask*0x9E3779B97F4A7C15ULL) ^ (u64(target)*0xBF58476D1CE4E5B9ULL);
            auto& e=entries[(hash^(hash>>32))&(entries.size()-1)];
            if(e.generation==generation&&e.mask==mask&&e.target==target)return e.value;
            const double v=covered_gain(mask,probability);
            e={mask,generation,target,v};
            return v;
        }
    };
'''+s[pos:]
s=s.replace('int c, const double* q) {','int c, const double* q, GainMemo* memo=nullptr, int target=0) {',1)
s=s.replace('return covered_gain(covered, [&](int j) { return 0.5 * (q[j + 1] - q[j]); });','''auto probability=[&](int j) { return 0.5 * (q[j + 1] - q[j]); };
        return memo?memo->get(target,covered,probability):covered_gain(covered,probability);''',1)
s=s.replace('        auto gain = [&](int t, int y, int c) {','        GainMemo gain_memo;\n        auto gain = [&](int t, int y, int c) {',1)
s=s.replace('diffb[y], c, q[t].data());','diffb[y], c, q[t].data(), &gain_memo, t);',1)
s=s.replace('struct ProbabilityHead {\n','struct ProbabilityHead {\n    mutable Design::GainMemo gain_memo;\n',1)
s=s.replace('    void update_probability() {','    void update_probability() {\n        gain_memo.reset();',1)
s=s.replace('dy, u.c, q[t].data());','dy, u.c, q[t].data(), &gain_memo, t);',1)
s=s.replace('diff[y], v.c, q[t].data());','diff[y], v.c, q[t].data(), &gain_memo, t);',1)
start=s.index('struct Perforation {')
a=s[:start];b=s[start:]
b=b.replace('struct Perforation {','struct Perforation {\n    mutable Design::GainMemo gain_memo;',1)
b=b.replace('return Design::covered_gain(cover, [&](int j) { return bad[u][j]; });','return gain_memo.get(u, cover, [&](int j) { return bad[u][j]; });',1)
b=b.replace('    void rebuild() {','    void rebuild() {\n        gain_memo.reset();',1)
s=a+b
(dest/'main.cpp').write_text(s)
(dest/'README.md').write_text('''# deval-gaincache

改良元: solutions/deval-vbranch-o3。

filler climb、再割当て、穴あけで使うcovered_gainを、対象番号と穴の集合でキャッシュする。先頭色確率を作り直すと世代番号を進め、古い値を使わない。外れた場合の浮動小数点演算順は元と同じ。16,384項の直接写像で、衝突時は完全なキーを検査する。探索回数、候補選択、注文処理と時間ガードは変更しない。
''')
print(dest,len(s.encode()))
