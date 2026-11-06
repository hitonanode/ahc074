"""Record each branch independently for training-only calibration of V."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEST=HERE.parent/'deval-vtrain'
src=(HERE.parent/'deval-vclean/main.cpp').read_text()
needle='        if(v<best) {\n            best=v;chosen=i;state=std::move(candidate);chosen_log=log.str();'
assert needle in src
src=src.replace(needle,'''        const int forced=int(env_real("DEVAL_FORCE_PICK",-1));
        if((forced<0&&v<best)||i==forced) {
            best=v;chosen=i;state=std::move(candidate);chosen_log=log.str();''')
DEST.mkdir(exist_ok=True)
(DEST/'main.cpp').write_text(src)
(DEST/'README.md').write_text('''# deval-vtrain

改良元: `solutions/deval-vclean`。候補ごとの教師データを作るため、`DEVAL_FORCE_PICK` が指定されたとき、その番号の候補を出力する。既定では親と同じく V の最小を選ぶ。注文処理は親と同じで、保存した各候補を標準スクリプトで 8 注文列に再生する。再学習に使う seed は 0–499 のみ。

生成は `solutions/deval-vselect/make_training.py`。提出用ではない。
''')
print('source bytes',len(src.encode()))
