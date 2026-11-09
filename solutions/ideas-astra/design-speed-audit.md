# Task 15 追加監査: 9候補finishの出力同一高速化

2026-11-09 09:38 JST開始。担当design_audit。親の指示に従い、読む・新規ファイルを編集するだけで調査し、コンパイル・ソルバ実行・重い解析は行っていない。基準行番号は `solutions/dcomp-combo-dual30/main.cpp`。`mdp-types` / `nextkey` / `ia-dirty-groups` と変更箇所を分けた。

**結論: 9候補ごとの巨大な不変表の再構築という100ms級の無駄は見つからなかった。最も具体的な新しい小候補は、穴あけの変更と無関係なgeometry/行走査を省く `ia-perf-lazy`。** 下記の2–10msは未測定の探索幅であり、速度改善の実績ではない。

## 費用の根拠と100msを見込まない理由

- 現dual30のユーザー提供値: finish9候補全体184ms、V23ms。
- 既存Clang native profile `20261108-173211_dcomp-t11-design-prof`（同時基準dcomp-combo-alt1、500seed、stdout500件同一）では、climb56.46ms、rematch86.86ms、穿孔run33.22ms（内cache7.03ms）。rematch内部はdonor24.16ms、target19.64ms、Hungarian23.45ms、gradient3.18ms、head rebuild22.06ms。rebuildとdonorは重複するため合算しない。`solutions/dcomp-notes/t11-design-prof-clang.json`。
- これは計測オーバーヘッド込みの旧基準で、dual30の通常時間そのものではない。だが、穿孔の小さなループ省略だけで100msを期待できないという規模の確認には使える。
- `make_solver` :10005はComparator::rebuild :329で38窓の印刷だけを更新する。720×720距離表、Interleave、MDP、lookaheadは構築していない。重い表の構築は最終設計選択後のmain :11221–11240に1回だけある。
- `deval::DesignValue` :10613は候補loopの外で1回構築され、GenericTable/PosetSumsは共有済み。固定quadratureも`samples_for` :10309でHごとに共有済み。

## 1. perf-lazy-geometry: 変更しないhead・対象・列を計算しない

**分類:** 出力同一高速化。**prototype:** `solutions/ia-perf-lazy/main.cpp`、READMEあり。親へ引き渡し済み、未コンパイル・未評価。

**元の箇所:** `Perforation::geometry_for` :9621、`refresh_cache` :9711–9733、`total_profit` :9759–9870。

### A. 署名比較は変更紙kだけ

元 :9777–9797は2色のheadそれぞれについて、cache_opacity/current opacityの署名を求めて比較する。`total_profit(k)`の前提は `opacity` と`cache_opacity`が紙kの1bitだけ異なること。kは固定headの一方であり、もう一方のheadは不変。non-owner対象の穴も不変なので、そちらの前後署名は必ず一致する。

```cpp
before = signature(k, cache_opacity);
after  = signature(k, opacity);
same = before == after;
fixed_starts = before.lo == after.lo &&
               (((before.cover ^ after.cover) & ~changed) == 0);
```

これで4回のsignatureを2回にする。`vector<bool> same(P)`も不要になり、ループ内のboolで足りる。

### B. non-ownerで同じ列の対象は全サンプル不変

`geometry_for(u,c)` は `c==columns[s.ded[u]]` なら常に辺なし。変更紙k以外の同列所有紙では、対象の穴は変わらず、唯一変わったdonor kは元々使えない。従って `cache_dirty[u]=false; dirty_samples[u]=0; continue;` とできる。owner自身はこの分岐より前に除外し、従来のowner補正へ残す。

### C. 行単位skipをgeometryより前へ

元 :9805は全256対象でgeometryを作り、8sampleそれぞれでowner/dirtyを検査する。次で同じ整数差分を保てる。

```cpp
for (u = 0; u < P; ++u) {
    if (ded[u] == k || dirty_samples[u] == 0) continue;
    geometry = geometry_for(u,c);
    for (sample = 0; sample < 8; ++sample) {
        if (!(dirty_samples[u] >> sample & 1)) continue;
        // 元のDP差分と同じ
    }
}
```

`refresh_cache`の`!all`呼出しでも`dirty_samples[u]==0`をall_geometryより前に除外する。元はcache_dirtyがtrueならall_geometryを作ってから8sampleを全部skipしていた。

### D. 穴追加時の変更前owner geometryは1列だけ

元 :9841–9846はownerごとに新旧両方のall_geometryを作る。ただし穴追加時に旧geometryを読むのは :9859の`old_geometry[changed_handle]`だけ。旧紙がその窓を覆っていたので、変更色の影響を1列の辺変更で計算する既存ロジックが根拠。

穴追加ではその1entryだけ作り、穴復元では従来どおりall_geometryを作る。読み忘れを避けるため、prototypeは同じ配列を残し、必要entryを明示的に初期化する。新geometryやowner補正のdouble順序は変えない。

**同一性の根拠:** 省く関数は整数mask/被覆情報の純粋な構築だけ。変更するcacheは辺が完全一致する行だけで、DP値は整数。profit/owner補正・受理比較・RNG・候補順・反復数はそのまま。`perf_cache_rows/skips`は不要と証明できた再構築を省くため変化し得る。

**既往との差:** `deval-geometry`は32sampleで共有するためgeometryをsample外へ出した案、`deval-perfsparse`は変更sampleのDPだけ更新する案。このprototypeはそれらがすでに入った後で、まだ作っている不要なgeometryと署名比較を消す。README検索とdcomp各報告では同じ追加案は見つからなかった。`ia-dirty-groups`はAnnealerの8lane群で、ここには触れない。

**規模/工数:** Clang穿孔全体33msという既存profileを上限の目安とし、追加短縮2–10msを仮置き。利得換算0.0006–0.003%程度で、単独0.03%案ではない。実装済み、検証・切り分け0.3–0.6h。

**最安probe:** dual30先頭の通常100–200seed compareをGCCとClang judge flagsで行い、stdout完全一致と候補ごとのV/設計一致を先に確認。時間はpaired `dv_finish_sec` とendで比較。Clangで明瞭な短縮がなければ深追いしない。採用は他の出力同一変更とstackして2000seedを500件単位で確認。

**リスク:** 同列non-ownerをownerと混同しないこと。old_geometryを1entryしか作らない分岐は穴追加に限る。既存のcache_opacity/opacityが1紙1bitだけ違う不変条件を壊す将来の複数穴operatorにはそのまま使えない。

## 2. singleton-row-copy: Hungarian費用行の完全重複を共有（低順位、未実装）

**箇所:** `rematch_probability` :4080–4128の費用行。anchor[i]<0、extra_holes(i)==0、beta[i]==0、同じ列c、同じ許容color（search_mode&4ならcolor自由）の行は、全jの条件・値が一致する。最初の該当行を作って以降はdouble行をcopyできる。乱数は行作成より前に消費済みなので変化しない。

**機序:** 現在もsingle_target/single_donorで高価な関数結果は共有している。残るmatrix列走査、条件、tail読出し、引算をrow copyへ置換するだけ。従って大きくはない。予想0–2ms、0–0.0006%、実装0.3h、未計測。まず何行重複するかのcountだけでよい。原則として上位へ渡さない。

**注意:** extra_holesやhead.betaを無視して共有してはいけない。beta0でも現在のheadとして存在することはあり得るが、値に影響しない。許容colorの同値性を明示する。pair行には適用しない。

## 再提案しない・大きくないもの

| 疑い | 確認結果 |
|---|---|
| 仕上げ用Solverが720×720距離表/MDPを毎回作る | 作らない。重い構築はmainで1回。make_solverの比較器rebuildは38窓だけ。 |
| Vが厳密汎用距離表/Sobolを9回作る | 共有済み。GenericTable ctorはPosetSums::get、samples_forはHをcache。 |
| 大きなSolver request cacheの初期化9回 | member初期化はあるが、数百KiB級×9の書込みであり100ms源ではない。NOINITへの過大期待を避ける。 |
| handle_lookupを9回構築 | 25×256の小ループ。共有可能でもsub-ms規模と思われ、構造分離の工数に見合いにくい。 |
| ProbabilityHeadの棄却cycleを元へ毎回rebuild | 次のcycleが上書きし、次iteration直前まで復元を遅延する修正が既に :4180付近へ入っている。 |
| 穴あけrun開始時の重複rebuild | constructorだけで構築し、runは再構築しない。既に修正済み。 |
| 非head donorの効用計算 | Perforation::rebuild :9887、ProbabilityHead::rebuild :3998とも最高weightだけ計算する省略済み。 |
| filler多項式cache | deval-gaincache、dcomp-climb-mask、dcomp-rematch-memoで既試験。rematch memoはGCC +7.56±2.17ms、run20261108-113533。 |
| target側を4head SIMDへ | dcomp-head4既試験。GCCでdonor4より約2.5ms遅く、Clang差も小さく不採用。dcomp-notes/PROGRESS:148。 |
| hole費用表引き | 既試験で悪化。Task8 +35.01±2.05ms、run20261108-110024。新しい理由なし。 |
| as_screen=0なのにscreen表がある | 定数0なのは旧ordinary screen。現在の候補生成/eliteがscreen情報を使うので丸ごと削除不可。 |
| Vの係数0のfeatureだけ消す | 高価なDPは残る。共通featureとの依存やVの加算順を守る工数に比べ小さい。 |

