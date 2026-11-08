"""Maintain the exact sorted compatible-pair list across accepted window moves."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/dcomp-nine/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:70]);s=s.replace(a,b)
sub('''    std::vector<int> rel;
    // a cycle''','''    std::vector<int> rel;
    std::vector<int> live;  // sorted compatible pairs in the accepted state
    // a cycle''')
a='''    int nvalid = 0;
    for (int p = 0; p < n8; p += 8) {
        const __m256i rel4 = _mm256_loadu_si256((const __m256i*)(nrel + p));
        const int good = _mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpgt_epi32(rel4, zero)));
        _mm256_storeu_si256(
            (__m256i*)(valid + nvalid),
            _mm256_add_epi32(_mm256_set1_epi32(p), _mm256_loadu_si256((const __m256i*)lanes[good].data())));
        nvalid += __builtin_popcount(good);
    }'''
b='''    // An old compatible pair survives unchanged iff its raw arcs are equal.
    // Every other compatible pair occurs in the newly closed acyclic list.
    // Both streams are sorted and disjoint; merge them in the original index
    // order so matching ties and every subsequent random choice stay identical.
    int nvalid=0,old_at=0,new_at=0;
    const int old_size=int(P.live.size());
    while(true) {
        while(old_at<old_size && ndir[P.live[old_at]]!=pdir[P.live[old_at]])++old_at;
        const int old_pair=old_at<old_size?P.live[old_at]:0x7fffffff;
        const int new_pair=new_at<nacyclic?pending[new_at]:0x7fffffff;
        if(old_pair==0x7fffffff && new_pair==0x7fffffff)break;
        if(old_pair<new_pair){valid[nvalid++]=old_pair;++old_at;}
        else {valid[nvalid++]=new_pair;++new_at;}
    }'''
sub(a,b)
sub('''        pairs.dir.swap(ndir);
        pairs.rel.swap(nrel);''','''        pairs.dir.swap(ndir);
        pairs.rel.swap(nrel);
        pairs.live.assign(valid.begin(),valid.begin()+nvalid);''')
a='''        if (pairs.rel[p]) valid[nvalid++] = p;'''
assert s.count(a)==2;s=s.replace(a,a+'\n    pairs.live.assign(valid.begin(),valid.begin()+nvalid);')
p=ROOT/'solutions/dcomp-nine-livepairs';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s)
(p/'README.md').write_text('''改良元: solutions/dcomp-nine

窓探索の受理済み状態について、互換なペア番号の昇順リストを保存する。試行後の互換ペアは「元のリストのうちraw relationが不変なもの」と「今回閉包を計算して非循環だったもの」の互いに重ならない和集合になる。この2つの昇順リストを併合し、毎回全ペアのrel配列を走査する処理を省く。受理とanneal→climbの移行で保存リストを更新する。

互換判定、費用、一覧の順序、同点処理、乱数列、固定反復数、候補数9、注文処理は変えない。CLOCK_SCALE、ログ、@paper/@ops、DesignStore、段の目印と実験スイッチ・プロファイラを保持。時間不足の切替なし。
''')
