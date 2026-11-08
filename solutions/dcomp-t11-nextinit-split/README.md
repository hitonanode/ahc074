改良元: solutions/dcomp-combo-alt1

next_costの不要初期化をなくし、fillerが空の時はgeneric境界の走査も省く。split.belowの全利用箇所はfillerの列挙内なので、この時のmaskは読まれない。計算項と加算順、候補順は同じ。

既存の固定予算、ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計による分岐は追加しない。
