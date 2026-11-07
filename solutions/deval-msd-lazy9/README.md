改良元: `solutions/deval-sort-msd9`（元はdeval-ordered8）。

上位bitのbucketの中を、貪欲マッチングがそのbucketを読む時だけ整列する。71ペアに達して停止した後のbucketは整列しない。読むキーとpair-idによる同値順は従来と同じ。プロファイルでは遅延した整列の時間をsortへ加え、greedyから引く。固定予算・出力同一の高速化案。
