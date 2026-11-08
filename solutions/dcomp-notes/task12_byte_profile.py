from pathlib import Path
S=Path(__file__).resolve().parents[1]
s=(S/'dcomp-t12-profile/main.cpp').read_text()
for name in ['byte_shift','byte_find','anchorize','screen_replay']:
 x='CfProfile cf_process{"process"};';assert s.count(x)==1;s=s.replace(x,x+'\nCfProfile cf_'+name+'{"'+name+'"};')
 x='&cf_process, &cf_run_plan';assert s.count(x)==1;s=s.replace(x,'&cf_'+name+', '+x)
for x,name in [('''    static int find_paper(const ByteOrder& o, int k) {''','byte_find'),('''    static void shift_byte(ByteOrder& o, int p, int dest) {''','byte_shift'),('''                                      OP_TAG(, const std::vector<uint8_t>& labels)) {''','anchorize'),('''        auto prepare_screen_replay = [&]() {''','screen_replay')]:
 assert s.count(x)==1;s=s.replace(x,x+'\n        CF_SCOPE('+name+');')
d=S/'dcomp-t12-byte-prof';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-t12-profile\n\npostの合法性再生をさらに分け、byte順序の探索・シフト・anchor変換・可換試行の準備のinclusive/exclusiveを測る。時計はscaled elapsed_sec。探索・出力を変えず、計測値で予算を変えない。既存ログ・trace・switch・段・DesignStoreを保持する。\n')
