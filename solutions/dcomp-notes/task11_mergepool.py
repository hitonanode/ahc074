from pathlib import Path
R=Path(__file__).resolve().parents[2]
B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
s=B
a='''        if (!tie_pooling || value >= tie_min + kTieGap) return;  // can never be within kTieGap of the choice'''
assert s.count(a)==1
s=s.replace(a,'''        if(!tie_pooling)return;
        if(value>=tie_min+kTieGap) {
            // A single merge can save one move before the final comparison.
            // Preserve such candidates, but still discard those beyond that bound.
            if(value>=tie_min+kTieGap+1)return;
            std::array<uint8_t,K> count{};bool twice=false;
            for(auto [k,d]:path)twice|=++count[k]==2;
            if(!twice)return;
        }''')
a='''        tie_pooling = false;
        const double v0 = plan_cost(path.size());'''
assert s.count(a)==1
s=s.replace(a,'''        tie_pooling = false;
        // Compare legal completed plans after the same cheap repeated-paper repair
        // the output path receives. The repair preserves each candidate's stack.
        const State unmerged_state=save();
        merge_double_moves(st0,path OP_TAG(,tags));
        for(auto& c:tie_pool) {
            restore(c.state);const size_t before=c.path.size();
            merge_double_moves(st0,c.path OP_TAG(,c.tags));
            if(c.path.size()!=before)c.value=plan_cost(c.path.size());
        }
        restore(unmerged_state);
        const double v0 = plan_cost(path.size());''')
d=R/'solutions/dcomp-t11-mergepool';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n最後のnear-tie選択で、同じ紙の二重移動をまとめる既存修復を全候補と現在解へ先に一回かけてから比較する。修復は完成stackを保存し、操作数だけを減らす。候補poolは二重移動を含む場合だけ通常のgapに1操作を加えた範囲まで保持し、修復前の値で捨てない。既存の補正係数は変えず、修復後の実際の操作数を使う。\n\n計画の生成・探索幅は親と同じ。追加修復は各候補一回、時計は使わない。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
