// One white paper and one black paper per window; every other window of them is a hole.
//
// Design (N = 64 windows, K = 192 papers):
//   papers 0..N-1    : paper j is opaque only at window j, in the more frequent color of window j
//                      among the P barcodes (the maximum-likelihood guess for the first request)
//   papers N..2N-1   : paper N+j is opaque only at window j, in the other color
//   papers 2N..K-1   : all holes (never visible, never moved)
// The initial order is 0, 1, ..., K-1 from the top, so window j starts showing paper j.
//
// Only the two papers of window j are opaque at window j, and the higher of them is the visible
// one. The paper with the wanted color is hidden under the other one, so it cannot be moved
// itself; instead the visible paper is moved to the bottom (d = K-1), below its partner. That move
// changes window j only, so a request takes exactly (number of windows whose color differs from
// the requested barcode) moves, and every request is displayed correctly (E = 0).
#include <array>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int N, K, P, R;
    std::cin >> N >> K >> P >> R;
    std::vector<std::string> barcodes(P);
    for (auto& s : barcodes) std::cin >> s;

    // Majority color of each window over the P barcodes (ties go to white).
    std::vector<int> ones(N, 0);
    for (const auto& s : barcodes) {
        for (int j = 0; j < N; j++) ones[j] += s[j] == '1';
    }
    std::vector<int> color(N);  // color currently shown at window j
    for (int j = 0; j < N; j++) color[j] = 2 * ones[j] > P ? 1 : 0;

    // paper_of[j][c]: the paper that shows color c at window j.
    std::vector<std::array<int, 2>> paper_of(N);
    std::string design;
    design.reserve(static_cast<size_t>(K) * (N + 1));
    for (int k = 0; k < K; k++) {
        std::string row(N, '.');
        if (k < 2 * N) {
            int j = k % N;
            int c = k < N ? color[j] : 1 - color[j];
            row[j] = static_cast<char>('0' + c);
            paper_of[j][c] = k;
        }
        design += row;
        design += '\n';
    }
    std::cout << design << std::flush;

    long long total_moves = 0, first_moves = 0;
    for (int r = 0; r < R; r++) {
        int request;
        std::cin >> request;
        if (request == -1) return 0;
        const std::string& target = barcodes[request];
        std::string out;
        int count = 0;
        for (int j = 0; j < N; j++) {
            int want = target[j] - '0';
            if (color[j] == want) continue;
            // Send the visible paper of window j to the bottom, uncovering its partner.
            out += std::to_string(paper_of[j][color[j]]) + ' ' + std::to_string(K - 1) + '\n';
            color[j] = want;
            count++;
        }
        std::cout << count << '\n' << out << std::flush;
        total_moves += count;
        if (r == 0) first_moves = count;
    }
    std::cerr << "moves = " << total_moves << '\n';
    std::cerr << "first_moves = " << first_moves << '\n';
    return 0;
}
