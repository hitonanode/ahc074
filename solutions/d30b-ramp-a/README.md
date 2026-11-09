改良元: solutions/d30a-reset6

焼きなましの4区間に使うreset需要の倍率を [2.0, 4.0, 6.0, 6.0] とする。共有前半と枝の後半は元の絶対区間番号を使い、反復回数・温度・乱数消費は変更しない。仕上げのfiller_climbとrematchは従来の6を使う。色確率や穿孔の倍率、Vは変更しない。

LOCAL_BENCHではD30B_RESET_RAMP=0で全区間を基準の6へ戻せる。D30B_RESET_S0〜S3で各区間の倍率を指定できる。既存D30A_RESETも維持する。新しいstderr指標ramp_reset_s0〜s3は区間倍率、ramp_finish_resetは仕上げ倍率。固定反復、CLOCK_SCALE、DesignStore、既存注釈と段目次を維持し、新しい時計・打切りは追加しない。
