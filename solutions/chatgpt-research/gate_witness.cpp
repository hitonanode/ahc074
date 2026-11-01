// A self-contained representation-capacity probe; this is not a contest solver.
// Enumerate every order of six sheets and exhibit an opposite target pair that
// comparisons cannot encode, but a balanced four-sheet first-visible gate can.
#include <algorithm>
#include <array>
#include <iostream>
#include <string>
#include <vector>

using Gate = std::array<int, 6>;  // -1 hole, 0 white, 1 black
using Order = std::array<int, 6>;

int display(const std::array<Gate, 3>& gates, const Order& order) {
    int mask = 0;
    for (int j = 0; j < 3; ++j) {
        for (int p : order) if (gates[j][p] >= 0) {
            mask |= gates[j][p] << j;
            break;
        }
    }
    return mask;
}

void count(const std::string& name, const std::array<Gate, 3>& gates, bool comma) {
    std::array<int, 8> counts{};
    std::array<Order, 8> witness{};
    Order order{0, 1, 2, 3, 4, 5};
    do {
        const int x = display(gates, order);
        if (!counts[x]) witness[x] = order;
        ++counts[x];
    } while (std::next_permutation(order.begin(), order.end()));
    std::cout << "  \"" << name << "\": {\"satisfying_000\": " << counts[0]
              << ", \"satisfying_111\": " << counts[7]
              << ", \"opposite_pair_feasible\": "
              << (counts[0] && counts[7] ? "true" : "false");
    for (int x : {0, 7}) if (counts[x]) {
        std::cout << ", \"witness_" << (x ? "111" : "000") << "\": [";
        for (int i = 0; i < 6; ++i) std::cout << (i ? ", " : "") << witness[x][i];
        std::cout << ']';
    }
    std::cout << '}' << (comma ? ",\n" : "\n");
}

int main() {
    // x0 is 0<1, x1 is 1<2, x2 is 2<0. Neither 000 nor 111 is a total order.
    const std::array<Gate, 3> binary{{
        Gate{1, 0, -1, -1, -1, -1},
        Gate{-1, 1, 0, -1, -1, -1},
        Gate{0, -1, 1, -1, -1, -1}
    }};
    auto three_black = binary;
    three_black[0][3] = 1;
    auto three_white = binary;
    three_white[0][4] = 0;
    auto four_balanced = binary;
    four_balanced[0][3] = 1;
    four_balanced[0][4] = 0;
    std::cout << "{\n  \"paper_count\": 6,\n  \"orders_enumerated_per_family\": 720,\n";
    count("binary_comparisons", binary, true);
    count("three_sheet_black_majority", three_black, true);
    count("three_sheet_white_majority", three_white, true);
    count("four_sheet_balanced", four_balanced, false);
    std::cout << "}\n";
}
