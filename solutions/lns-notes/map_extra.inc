// Regional repair deliberately has no old-pair-loss screen. The fixed region
// includes generic and optional handle windows; every other physical window stays put.
struct LnsMapConfig {
    bool active=false;
    u64 windows=0, salt=0;
    std::vector<int> groups;
    double temperature=.12;
    std::vector<std::pair<int,int>> old_pairs;
    std::vector<std::pair<int,int>> preferred_pairs;
    std::array<int,64> origin_codes{};
};
LnsMapConfig lns_map;
