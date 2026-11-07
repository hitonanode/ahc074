from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
base=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
for name,kind in [('deval-edit4','edit'),('deval-blockbad','bad')]:
 s=base
 if kind=='edit':
  old='''    struct Edit {
        int paper, anchor;
        OP_TAG(uint8_t tag = kOpRepair;)  // the label of its move (anchorize sets it; a new edit is a repair)
    };'''
  new='''    struct Edit {
        uint8_t paper;
        OP_TAG(uint8_t tag=kOpRepair;)  // LOCAL_BENCH labels occupy the otherwise unused padding byte.
        int16_t anchor;
        Edit() = default;
        Edit(int k,int a OP_TAG(,uint8_t t=kOpRepair))
            : paper(uint8_t(k)), OP_TAG(tag(t),) anchor(int16_t(a)) {}
    };
    static_assert(sizeof(Edit)==4);'''
  assert old in s;s=s.replace(old,new,1)
 else:
  s=s.replace('void prepare_post_context(const State& initial) {','void prepare_post_context(const State& initial,int u) {',1)
  s=s.replace('prepare_post_context(initial);','prepare_post_context(initial,u);',1)
  s=s.replace('c.blocks[0][j] = {paper[k].opaque, paper[k].black};','c.blocks[0][j] = {paper[k].opaque, (paper[k].black ^ A[u]) & paper[k].opaque};',1)
  start=s.index('auto evaluate = [&](const std::vector<Edit>& trial)')
  end=s.index('            auto& path = path_buffer;',start)
  b=s[start:end]
  b=b.replace('u64 seen = 0, view = 0;','u64 seen = 0;',1)
  b=b.replace('if ((disp ^ A[u]) & cov & ~seen) return false;','if (disp & ~seen) return false;',1)
  b=b.replace('                    view |= disp & ~seen;\n','',1)
  b=b.replace('if (view != A[u]) return false;','if (seen != ~u64(0)) return false;',1)
  s=s[:start]+b+s[end:]
  s=s.replace('// A block maps incoming coverage to the first color on its opaque windows. Combining','// A block stores coverage and the target-mismatching windows of its first opaque papers. Combining',1)
 d=ROOT/'solutions'/name;d.mkdir(exist_ok=True)
 (d/'main.cpp').write_text(s)
 desc='編集の紙番号とanchorを4バイトの構造体へ詰める。紙番号は0〜191、anchorは−1〜191なので値は変わらない。LOCAL_BENCHの操作ラベルも保持する。' if kind=='edit' else '後処理の初期スタックの疎テーブルに、表示色ではなく要求色との不一致を保存する。同じ被覆結合で不一致を求め、試行ごとのXORと表示色の集計を省く。設計は全窓を覆うため、末尾までの走査では必ず全被覆になる。'
 (d/'README.md').write_text(f'# {name}\n\n改良元: solutions/deval-vbranch-o3。\n\n{desc}\n\n探索予算・浮動小数演算・時間ガードは同じ。\n')
 print(name,len(s.encode()))
