"""Remove the experimental objective from the annealer's hot path."""
from pathlib import Path
import re
from make_col import refresh_contents
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
DEST=HERE.parent/'deval-vclean'

def main():
    src=(HERE.parent/'deval-vbeam/main.cpp').read_text()
    parent=(ROOT/'solutions/argon-des-perf-latew105/main.cpp').read_text()
    begin='    // ==== Design annealing ===='
    end='    // ==== Filler climb: columns of the units for the filler value ===='
    anneal=parent[parent.index(begin):parent.index(end)]
    anneal=anneal.replace('void anneal(double seconds, int fixedIterations = 0) {',
        'void anneal(double seconds, int fixedIterations = 0, int firstSegment = 0, int endSegment = 4) {')
    anneal=anneal.replace('for (int s = 0; s < kAnnealSegments; s++) {',
                          'for (int s = firstSegment; s < endSegment; s++) {')
    a=src.index('                    if(D.elite_states')
    b=src.index('\n                }\n                int type',a)
    hook=src[a:b]
    temperature='                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);'
    assert temperature in anneal
    anneal=anneal.replace(temperature,temperature+'\n'+hook)
    src=src[:src.index(begin)]+anneal+src[src.index(end):]
    lo=src.index('    double hcost(int j) const {')
    hi=src.index('    // The reset demand',lo)
    src=src[:lo]+'    double hcost(int j) const { return hole_cost_of(hn[j][0], hn[j][1], reset_targets[j]); }\n'+src[hi:]
    src=re.sub(r'    double gc\(const Unit& u\) const \{[^\n]+',
        '    double gc(const Unit& u) const { return u.b < 0 ? 0 : gcost[u.a][u.b] * 2; }',src)
    src=re.sub(r'^.*des->local_objective.*\n','',src,flags=re.M)
    src=src.replace('    double local_objective=0;\n','')
    src=src.replace('    long long light_requests=0;','    long long light_requests=0,hard_light_requests=0;')
    src=src.replace('    Moves process(int u) {','    int processed_requests=0;\n    Moves process(int u) {\n        const double remaining=std::max(0.,(1024.-processed_requests++)/1024.);')
    src=src.replace('        bool light=false;','        int light=0;')
    src=src.replace('        light=elapsed_sec()>DEVAL_REQUEST_LIMIT;',
        '        const double now=elapsed_sec();\n        light=now>DEVAL_REQUEST_LIMIT-.30*remaining?2:now>1.84-.12*remaining?1:0;')
    src=src.replace('light=now>DEVAL_REQUEST_LIMIT?2:now>1.84?1:0;',
                    'light=now>DEVAL_REQUEST_LIMIT-.30*remaining?2:now>1.84-.12*remaining?1:0;')
    src=src.replace('        light_requests+=light;',
        '        light_requests+=light>0;\n        hard_light_requests+=light==2;')
    src=src.replace('static const bool neutral_enabled = [] {','static const bool neutral_config = [] {')
    src=src.replace('        OP_TAG(if (neutral_enabled) ++request_counter;)',
        '        const bool neutral_enabled=neutral_config && light==0;\n        OP_TAG(if (neutral_enabled) ++request_counter;)')
    src=src.replace('            if(light) {','            if(light==2) {')
    src=src.replace('#define DEVAL_REQUEST_LIMIT 1.72','#define DEVAL_REQUEST_LIMIT 1.90')
    if 'std::cerr << "hard_light_requests = "' not in src:
        src=src.replace('    std::cerr << "light_requests = " << solver.light_requests',
            '    std::cerr << "hard_light_requests = " << solver.hard_light_requests << \'\\n\';\n    std::cerr << "light_requests = " << solver.light_requests')
    src=src.replace('env_int("DEVAL_CANDIDATES"):2','env_int("DEVAL_CANDIDATES"):4')
    src=src.replace('env_real("DEVAL_MODE",5)','env_real("DEVAL_MODE",1)')
    src=src.replace('kClimbIters = int(154000 * ITER_SCALE), kMatchIterations = 4',
                    'kClimbIters = int(50000 * ITER_SCALE), kMatchIterations = 2')
    src=refresh_contents(src)
    assert 'local_objective' not in src
    assert len(src.encode())<=520000
    DEST.mkdir(exist_ok=True)
    (DEST/'main.cpp').write_text(src)
    (DEST/'README.md').write_text('''# deval-vclean

改良元: `solutions/deval-vbeam`（焼きなまし内部の更新処理は `solutions/argon-des-perf-latew105` に戻す）。

既定では前半 2 段を共有し、後半 2 段を 4 分岐する。分岐の反復数は各 1/4 で、全反復数は親の SOTA と同じ。各候補を filler climb 50,000 回、再割当て 2 回、穴あけと最終再割当てまで仕上げ、V16 で選ぶ。V は対象別固定積分点と解析的な不一致数補正を使う。

実験で使った局所目的関数の分岐を内側の更新から取り除く。候補数・共有段数・分岐数などの実験用環境変数は deval-vbeam と同じだが、局所目的関数と温度変更は使わない。

提出時は残注文の比率を q として、1.84 − 0.12q 秒から中立探索を省略し、1.90 − 0.30q 秒から通常計画の最初の合法解を使う。残注文を処理する時間を予約する。LOCAL_BENCH では両方とも無効。追加の設計候補は設計経過 1.12 秒以降に開始しない。保存される設計は選択済みの設計。元の診断・段の目印・DesignStore を維持する。

再生成: `solutions/deval-vselect/make_clean.py`。
''')
    print('source bytes',len(src.encode()))
if __name__=='__main__':main()
