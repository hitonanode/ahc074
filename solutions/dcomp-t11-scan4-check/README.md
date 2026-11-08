改良元: solutions/dcomp-combo-alt1

next_costの列内scanで、同じ列の連続4紙の項をAVX2 gatherで得る。色の初出depthとMDPの2bit列も同じ紙順で更新する。4項のdouble加算は元の順序を明示的に維持し、列の境界や64/128 checkpointを跨がない。元のscalar next_costでも再計算し、double全bitを照合する。

違う列が混ざる4紙はscalar経路を使うため、列の並び順を仮定しない。探索予算・ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreは保持。fast-mathや時計による切替は使わない。
