from pathlib import Path
S=Path(__file__).resolve().parents[1]
def make(name,source,desc,base='dcomp-combo-dual25'):
 d=S/name;assert not d.exists(),d;d.mkdir();(d/'main.cpp').write_text(source)
 (d/'README.md').write_text(f'改良元: solutions/{base}\n\n'+desc+'\n\n固定予算・時計による軽量化なし。CLOCK_SCALE、DesignStore、@paper/@ops、ログ・実験スイッチ・profiler、段と目次を保持する。\n')
b=(S/'dcomp-combo-dual25/main.cpp').read_text()
p=b
names=['record_future','merge_moves','secondary','post_secondary','post_neutral','post_ordinary']
p='#define COLFAST_PROFILE 1\n'+p
p=p.replace('#define CF_SCOPE(name) CfScope', '\n'.join('CfProfile cf_'+n+'{"'+n+'"};' for n in names)+'\n#define CF_SCOPE(name) CfScope')
p=p.replace('&cf_choose_fillers, &cf_post_setup,',','.join('&cf_'+n for n in names)+', &cf_choose_fillers, &cf_post_setup,')
p=p.replace('auto record_future = [&](double cost) {','auto record_future = [&](double cost) {\n            CF_SCOPE(record_future);')
p=p.replace('void merge_double_moves(const State& st0, Moves& path OP_TAG(, std::vector<uint8_t>& tags)) {','void merge_double_moves(const State& st0, Moves& path OP_TAG(, std::vector<uint8_t>& tags)) {\n        CF_SCOPE(merge_moves);')
p=p.replace('CF_SCOPE(post);','CF_SCOPE(post);\n#if COLFAST_PROFILE\n        CfScope role_scope(secondary_neutral?cf_post_secondary:neutral_collect?cf_post_neutral:cf_post_ordinary);\n#endif')
p=p.replace('if(round==1) {\n                    int second_count=0;','if(round==1) {\n                    CF_SCOPE(secondary);\n                    int second_count=0;')
make('dcomp-t12-profile',p,'追加親、通常・中立のpost、family前修復の時間をCOLFAST_PROFILEで分けて測定する。探索・結果は親と同じ。')
# Only path/tags and merge counters change; save/restore is redundant.
q=b.replace('const auto raw_state=save();const auto raw_ops=ops;OP_TAG(const auto raw_tags=op_tags;)\n            auto screened=ops;OP_TAG(auto screened_tags=op_tags;)','auto raw_ops=std::move(ops);OP_TAG(auto raw_tags=std::move(op_tags);)\n            auto screened=raw_ops;OP_TAG(auto screened_tags=raw_tags;)')
q=q.replace('restore(raw_state);ops=raw_ops;OP_TAG(op_tags=raw_tags;)','ops=std::move(raw_ops);OP_TAG(op_tags=std::move(raw_tags);)')
make('dcomp-t12-rawcopy',q,'family選別前の修復で状態の不要なsave/restoreを省く。merge_double_movesは紙順と記録を変更せず、操作列と計測カウンタだけを変更する。元の操作列はmoveで退避・復元し、修復用だけをコピーする。候補の順と費用計算は変えない。')
