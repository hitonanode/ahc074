"""Clear/rebuild only nonzero relation costs, preserving pair and matching order."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
s = (ROOT / 'solutions/dcomp-nine-livepairs/main.cpp').read_text()

def sub(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)

sub('    std::vector<int> live;  // sorted compatible pairs in the accepted state',
    '''    std::vector<int> live;  // sorted compatible pairs in the accepted state
    std::vector<int> scratch_live;  // nonzero entries of the scratch nrel buffer''')
sub('''    const int n8 = P.n8;
    static const''', '''    const int n8 = P.n8;
    // Every other scratch entry is already zero. After an accepted move the
    // two live lists swap along with their corresponding relation buffers.
    for(int p:P.scratch_live)nrel[p]=0;
    static const''')
sub('''            const __m256i kept = _mm256_and_si256(rsame, _mm256_loadu_si256((const __m256i*)(prel + p)));
            _mm256_storeu_si256((__m256i*)(nrel + p), kept);
''', '')
sub('''        if(old_pair<new_pair){valid[nvalid++]=old_pair;++old_at;}''',
    '''        if(old_pair<new_pair){valid[nvalid++]=old_pair;nrel[old_pair]=prel[old_pair];++old_at;}''')
sub('''        else {valid[nvalid++]=new_pair;++new_at;}
    }
#if DESIGN_PROFILE >= 3''', '''        else {valid[nvalid++]=new_pair;++new_at;}
    }
    P.scratch_live.assign(valid,valid+nvalid);
#if DESIGN_PROFILE >= 3''')
sub('''        pairs.live.assign(valid.begin(),valid.begin()+nvalid);
        if (mv.swindow)''', '''        pairs.live.swap(pairs.scratch_live);
        if (mv.swindow)''')
p = ROOT / 'solutions/dcomp-nine-sparserel'
p.mkdir(exist_ok=True)
(p / 'main.cpp').write_text(s)
(p / 'README.md').write_text('''改良元: solutions/dcomp-nine

dcomp-nine-livepairsの互換ペア一覧の差分更新に加え、窓探索のrelation費用配列を疎に更新する。配列の非ゼロ要素は互換ペアだけなので、作業用配列の直前の非ゼロ要素だけ消し、元の互換ペアのうち不変な費用と新たに計算した費用だけ書く。受理時は状態と作業用の配列を交換するのに合わせて、それぞれの非ゼロ一覧も交換する。残りの要素は厳密にゼロのまま。

全ペアのSIMD走査から費用配列の読み出し・マスク・書き込みを省く。互換判定、閉包、並べ替えキー、ペアの順序、乱数列、固定反復数、9候補、注文処理は変えない。CLOCK_SCALE、ログ、@paper/@ops、DesignStore、段の目印、実験スイッチとプロファイラを保持し、時間不足の切替は加えない。
''')
