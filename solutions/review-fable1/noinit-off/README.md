# noinit-off

review-fable1 の検査用コピー。solutions/final-time-pace/main.cpp の NOINIT / NOINIT_CLANG を空にしただけ（-ftrivial-auto-var-init の下で全部の局所変数が 0 で埋まる）。固定反復の設計で出力を元と比べ、NOINIT の配列が書く前に読まれていないことを確かめる。
