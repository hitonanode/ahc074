from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-t11-fast-nomemo/main.cpp').read_text()
start=B.index('    Moves post_optimize(const State& initial,')
end=B.index('    // ==== Post-processing: two deletions and one repair (eject) ====',start)
for mode in ['memo','both']:
 part=B[start:end]
 part=part.replace('    Moves post_optimize(const State& initial,','    template<bool Memo'+(',bool Prefix'if mode=='both'else'')+'>\n    Moves post_optimize_impl(const State& initial,',1)
 part=part.replace('cfg.memo','Memo')
 if mode=='both':part=part.replace('cfg.prefix','Prefix')
 wrapper='''    // Dispatch once per edit pass; all runtime experiment settings remain usable.
    Moves post_optimize(const State& initial,Moves path,int u OP_TAG(,std::vector<uint8_t>& tags),
                        bool eject=false,bool delete_only=false) {
        const auto& cfg=search_config();
'''
 for memo in [True,False]:
  if mode=='both':
   for prefix in [True,False]:
    wrapper+=f'        if(cfg.memo=={str(memo).lower()} && cfg.prefix=={str(prefix).lower()})return post_optimize_impl<{str(memo).lower()},{str(prefix).lower()}>(initial,std::move(path),u OP_TAG(,tags),eject,delete_only);\n'
  else:wrapper+=f'        if(cfg.memo=={str(memo).lower()})return post_optimize_impl<{str(memo).lower()}>(initial,std::move(path),u OP_TAG(,tags),eject,delete_only);\n'
 wrapper+='        std::abort();\n    }\n\n'
 s=B[:start]+part+wrapper+B[end:]
 d=R/'solutions'/('dcomp-t11-postspecial-'+mode);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-t11-fast-nomemo\n\npost_optimizeのMEMO'+('とPREFIX'if mode=='both'else'')+'をtemplate boolにし、呼出しの最初だけruntime設定で分岐する。大きな試行評価の内側で固定条件を繰り返し読む必要をなくす。両方の実験設定を残し、演算・候補順・探索回数を変えない。\n\nGCCとClangで親に対するbyte一致と対応時間を測る。時計による切替なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
