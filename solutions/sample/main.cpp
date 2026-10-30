// The official sample solution (Python, in the problem statement) ported to C++, as a baseline.
// Paper k shows pattern A_k. For a request a < K, the top paper is moved to the bottom until paper a
// is on top; requests a >= K are left wrong.
#include <iostream>
#include <string>
#include <vector>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int N, K, P, R;
    std::cin >> N >> K >> P >> R;
    std::vector<std::string> patterns(P);
    for (auto& s : patterns) std::cin >> s;
    std::string design;
    for (int k = 0; k < K; k++) design += patterns[k] + '\n';
    std::cout << design << std::flush;

    int top = 0;
    long long total_moves = 0, skipped = 0;
    for (int r = 0; r < R; r++) {
        int request;
        std::cin >> request;
        if (request == -1) return 0;
        int count = request < K ? (request - top + K) % K : 0;
        if (request >= K) skipped++;
        std::string out = std::to_string(count) + '\n';
        for (int i = 0; i < count; i++) {
            out += std::to_string(top) + ' ' + std::to_string(K - 1) + '\n';
            top = (top + 1) % K;
        }
        total_moves += count;
        std::cout << out << std::flush;
    }
    std::cerr << "moves = " << total_moves << '\n';
    std::cerr << "skipped = " << skipped << '\n';
    return 0;
}
