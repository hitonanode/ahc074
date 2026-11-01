# joint-pairing（研究用・提出用ではない）

改良元: PR #52 の solutions/frontier-lattice（f90b9ee）。reference.hpp はその main.cpp の無変更コピー。imp-lean の公開入力設計・オンライン処理を分離し、表示関数と70商品ペアを同時探索する。

main.cpp は base（公開バーコードから元設計を書き出す）、refit（変更した表示関数と70ペアから列配置を再最適化）、play（保存設計を検査し、対話で注文を処理）の3モード。engine.cpp は720順序の実現集合と合法な有向最短距離のC ABI。optimize.py は固定表示関数に対する厳密70辺マッチング。pool.py は1窓・同じ元辺の窓ブロックの規則変更を列挙する。prepare.py は独立模擬注文だけで候補を選び、未使用注文列は読まない。

全15辺の逆色2枚窓を保護する。残り窓は黒1白1の30規則、または黒2白2の90規則。4枚規則は両商品の実現集合を別々に検査する。LP下界と必要時のMILPを使い、許容誤差内で最適性を確認した整数マッチングのみ採用。2秒制限を外した研究であり、playの所要時間には設計時間を含まない。結果と採否はREPORT.md。

## 最小再現（repoルートから）

Python 3.11以降、NumPy 2.3.5、SciPy 1.17.0、x86_64/AVX2、GCC14.2で検証。下記のパスを明示すれば /mnt/data は不要。

```sh
D=solutions/joint-pairing
mkdir -p "$D/build" tools/target/release
python -m pip install numpy==2.3.5 scipy==1.17.0
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 "$D/main.cpp" -o "$D/build/driver"
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 -fPIC -shared "$D/engine.cpp" -o "$D/build/libjoint.so"
# 公式Rustテスターを利用する場合。ローカル研究では tester.cpp の移植版を使用した。
(cd tools && cargo build --release --bin tester)
python "$D/generate.py" --start 6001 --count 32
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python "$D/prepare.py" --seeds 6001-6033 --out "$PWD/runs/joint-designs" --driver "$PWD/$D/build/driver" --lib "$PWD/$D/build/libjoint.so" --threads 4
```

base/refitの探索回数は MAP_ITERS=12000、GOPT_STEPS=3000、ANNEAL_ITERS=6000000、CLIMB_ITERS=30000。playは JOINT_STAGE=play JOINT_INPUT=<保存設計> JOINT_FORCE_BFS=1 を指定する。候補は元設計、再マッチングのみ、2枚規則8個、4枚規則4個。模擬注文2本×1024で候補選択。

主要stderr: total_moves（操作総数）、self_wrong（表示失敗）、lattice_nonlinear_queries（4枚窓に依存する注文数）、generic_moves（汎用紙操作数）、model_cost（列再配置後の模型平均）。
