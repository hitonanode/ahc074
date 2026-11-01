#include <algorithm>
#include <array>
#include <iostream>
#include <map>
#include <set>
#include <vector>

int main() {
    std::vector<std::array<int, 3>> orders;
    std::array<int, 3> p{0, 1, 2};
    do { orders.push_back(p); } while (std::next_permutation(p.begin(), p.end()));
    // At one window a paper has exactly three possible symbols. This enumeration is exhaustive,
    // including the all-hole column whose display is the default white in all states.
    std::set<int> functions;
    for (int a = 0; a < 27; ++a) {
        std::array<int, 3> color{};
        int x = a, f = 0;
        for (int& c : color) { c = x % 3; x /= 3; }
        for (int s = 0; s < 6; ++s) {
            int c = 0;
            for (int k : orders[s]) if (color[k] != 2) { c = color[k]; break; }
            f |= c << s;
        }
        functions.insert(f);
    }
    std::cout << "column_functions_on_all_six_orders = " << functions.size() << '\n';
    std::map<int, int> histogram;
    for (int mask = 0; mask < 64; ++mask) {
        if (__builtin_popcount(unsigned(mask)) != 4) continue;
        std::set<int> image;
        for (int f : functions) {
            int out = 0, j = 0;
            for (int s = 0; s < 6; ++s) if (mask >> s & 1) out |= (f >> s & 1) << j++;
            image.insert(out);
        }
        ++histogram[int(image.size())];
        std::cout << "states =";
        for (int s = 0; s < 6; ++s) if (mask >> s & 1) {
            std::cout << ' ';
            for (int v : orders[s]) std::cout << v;
        }
        std::cout << " ; expressible = " << image.size() << " ; missing =";
        for (int f = 0; f < 16; ++f) if (!image.count(f)) {
            std::cout << ' ';
            for (int j = 0; j < 4; ++j) std::cout << (f >> j & 1);
        }
        std::cout << '\n';
    }
    for (auto [n, count] : histogram)
        std::cout << "four_order_subsets_with_" << n << "_functions = " << count << '\n';
    // A fixed all-hole window cannot ask an independent generic layer to repair only some
    // orders: if no local paper is opaque then every local order exposes that layer.
}
