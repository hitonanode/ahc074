"""Assemble only individually validated exact changes; compiler budgets stay identical."""
from pathlib import Path
import argparse,sys
sys.dont_write_bytecode=True
from task11_stack import stack
p=argparse.ArgumentParser();p.add_argument('--geometry',action='store_true');a=p.parse_args()
R=Path(__file__).resolve().parents[2]
changes=['dcomp-t11-anchor-lazy','dcomp-t11-partial-cache','dcomp-t11-nextinit','dcomp-t11-latememo']
if a.geometry:changes.append('dcomp-t11-direct-geometry')
d=stack('dcomp-t11-fast-late',changes,'両コンパイラで検証した出力同一高速化の合成。合法性再生後のend-memoを使う。')
p=d/'main.cpp';s=p.read_text()
# Preserve GCC's token sequence; skip the unused links only on Clang, where it won.
old='''            std::array<u64, 3> moved{}, breaks{};
            const bool use_screen = screened_eval;
            screened_eval = false;
            auto next = use_screen ? anchor_screen.next : initial_next;'''
assert s.count(old)==1
s=s.replace(old,'''#if defined(__clang__)
            const bool use_screen=screened_eval;screened_eval=false;
            if(!use_screen || (cfg.memo && !cfg.late_memo)
#ifdef SCREEN_LINK_CHECK
               || true
#endif
            ) {
            std::array<u64,3> moved{},breaks{};
#else
            std::array<u64, 3> moved{}, breaks{};
            const bool use_screen = screened_eval;
            screened_eval = false;
#endif
            auto next = use_screen ? anchor_screen.next : initial_next;''')
old='''            auto& path = path_buffer;
            path.clear();''';assert s.count(old)==1
s=s.replace(old,'#if defined(__clang__)\n            }\n#endif\n'+old)
# Skip solved first-color tests only on Clang; arithmetic and iteration order stay fixed.
old='    std::array<NextPaper, K> next_paper;';assert s.count(old)==1
s=s.replace(old,old+'\n#if defined(__clang__)\n    std::array<uint8_t,64> next_colors{};\n#endif')
old='            next_paper[k] = {uint16_t(k * stride), uint8_t(column_color[k]), uint8_t(colmdp_type[k])};';assert s.count(old)==1
s=s.replace(old,old+'\n#if defined(__clang__)\n            if(column_color[k]>=0)next_colors[column_color[k]>>1]|=uint8_t(1U<<(column_color[k]&1));\n#endif')
old='''                do {
                    const auto& np=next_paper[key[i]];
                    if(first[np.color]<0)first[np.color]=depth;
                    cost+=depth_terms[np.offset+depth];++depth;
                    if(mdp_scan)code=(code<<2)|np.type;
                    ++i;
                } while(i<end && (next_paper[key[i]].color>>1)==c);''';assert s.count(old)==1
n=(R/'solutions/dcomp-t11-nextcolors/main.cpp').read_text()
begin=n.index('                int seen=int(first[2*c]>=0)')
end=n.index('                rank[c]=depth;',begin)
new=n[begin:end].rstrip('\n')
s=s.replace(old,'#if defined(__clang__)\n'+new+'\n#else\n'+old+'\n#endif')
p.write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n出力同一の要求高速化を合成する。anchor候補は固定配列にし、最後の勝者だけanchorizeする。部分MDPの列内紙ID列を正確なkeyでcacheし、prefix hitで不要な初期化をしない。end-memoは合法性再生を通った後で検索し、完成順序の192byteを全照合する。'+('修復区間の端点はtop-two-layer prefixから直接求める。'if a.geometry else '')+'\n\nClangだけでは、表示検査済みの候補の不要なリンク配列構築を省き、next_costで既に見つかった色を再検査しない。両方ともGCCでは元の実装を使う。コンパイラで探索の件数や予算は変えない。加算順・候補順・出力は保持する。MEMO/LATE_MEMOと検証用の旧経路を残す。\n\n設計9候補、要求方針・ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。\n')
