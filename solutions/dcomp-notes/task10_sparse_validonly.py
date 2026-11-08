from pathlib import Path
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
for mode in ['loose','unified']:
 s=base.replace('#if !defined(__clang__)\n','#if 1 // Only listed valid costs are ever read.\n')
 s=s.replace('    std::vector<int> scratch_live;  // nonzero entries of the scratch nrel buffer\n','')
 a='''    // Every other scratch entry is already zero. After an accepted move the
    // two live lists swap along with their corresponding relation buffers.
    for(int p:P.scratch_live)nrel[p]=0;'''
 assert s.count(a)==1;s=s.replace(a,'''    // Costs outside the valid list are deliberately unspecified. matching_cost
    // reads only valid[], and the next proposal reads only P.live. No clearing. ''')
 assert s.count('    P.scratch_live.assign(valid,valid+nvalid);')==1;s=s.replace('    P.scratch_live.assign(valid,valid+nvalid);','')
 assert s.count('        pairs.live.swap(pairs.scratch_live);')==1;s=s.replace('        pairs.live.swap(pairs.scratch_live);','        pairs.live.assign(valid.begin(),valid.begin()+nvalid);')
 # The profile observes validity, not the now-unspecified costs of invalid pairs.
 assert s.count('ap.new_valid += !pairs.rel[p];')==1;s=s.replace('ap.new_valid += !pairs.rel[p];','ap.new_valid += !std::binary_search(pairs.live.begin(),pairs.live.end(),p);')
 if mode=='unified':
  a='''    for(int p:P.live)nrel[p]=prel[p]*int(ndir[p]==pdir[p]);
#else
#endif
    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);'''
  b='''    u64 live_bits[512];std::fill(live_bits,live_bits+P.words,u64(0));
    for(int p:P.live) {
        nrel[p]=prel[p];
        live_bits[p>>6]|=u64(ndir[p]==pdir[p])<<(p&63);
    }
    for(int k=0;k<nacyclic;++k) {
        const int p=pending[k];nrel[p]=1+relations.sums.both_of(closures[k]);
        live_bits[p>>6]|=u64(1)<<(p&63);
    }
#else
    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);
#endif'''
  assert s.count(a)==1;s=s.replace(a,b)
  a=s.index('    // Build a compact bitset, then enumerate in ascending pair order.');b=s.index('    int nvalid=0;',a)
  s=s[:a]+'    // Retain the original ascending pair order.\n'+s[b:]
 p=r/'solutions'/('dcomp-sparse-'+mode);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\n疎な窓評価を両コンパイラで再検討。費用配列のうち読むのはvalid/liveに載った場所だけなので、無効な場所の0初期化を省く。新しいlive一覧も試行ごとにコピーせず、受理時だけvalidから更新する。'+('旧validの費用コピーとbitset更新、新しい閉包費用とbitset更新をそれぞれ統合する。' if mode=='unified' else '')+' AS_PROFILEの新規validカウントもliveで判定し、従来どおり。\n\n初期化とclimbへの移行では全費用を再構築。matching列挙順・乱数・費用演算は不変。探索予算・ログ・実験スイッチを保持、時間fallbackなし。\n')
