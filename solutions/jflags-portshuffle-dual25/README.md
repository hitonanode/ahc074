# jflags-portshuffle-dual25（dual25 の std::shuffle だけをライブラリによらない手順に）

改良元: `solutions/dcomp-combo-dual25`。原因を分けるための版で、jflags-portable-dual25 から std::sort の置き換えだけを戻したもの。3 か所の `std::shuffle` だけを `stdx::shuffle`（libstdc++ 13 の手順）にした。libstdc++ でビルドしたときの出力は改良元と同じになるはず。
