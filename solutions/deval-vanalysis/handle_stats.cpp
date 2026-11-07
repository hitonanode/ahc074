// Per-handle statistics of the V16 handle model for saved designs (stdin: design paths).
// For each design and handle c: x (color-0 hole demand), y (color-1), nt (targets of column c),
// p_static (strength 2), p_final (after 2 updates), raw0/raw1 (expected mismatches by requested
// color under p_final), fix0/fix1 (residual fixes after the filler cover). Text output, one line
// per design: H then 9 numbers per handle.
#include "value_v16.hpp"
#include <fstream>
#include <iostream>
#include <iomanip>
int main() {
    std::string path;
    std::cout << std::setprecision(6);
    while (std::getline(std::cin, path)) {
        std::ifstream in(path);
        if (!in) return 1;
        auto s = deval::State::read(in);
        auto p = s.probabilities(2.);
        const auto p0 = p;
        const deval::Donors donors(s, p);
        auto r = deval::expectation(s, donors, p, deval::samples_for(s.H), 16, 1.6);
        for (int step = 1; step <= 2; ++step) {
            for (int c = 0; c < s.H; ++c) {
                const double a = r.flips[c][1] / std::max(1.e-4, 1 - p[c]);
                const double b = r.flips[c][0] / std::max(1.e-4, p[c]);
                const double reset = 2 * s.nt[c];
                const double next = (a + reset * (s.xy[c][1] > s.xy[c][0])) / std::max(1., a + b + reset);
                p[c] = .5 * p[c] + .5 * next;
            }
            r = deval::expectation(s, donors, p, deval::samples_for(s.H), 16, 1.6);
        }
        std::cout << s.H;
        for (int c = 0; c < s.H; ++c) {
            const double raw0 = s.xy[c][0] * p[c], raw1 = s.xy[c][1] * (1 - p[c]);
            std::cout << ' ' << s.xy[c][0] << ' ' << s.xy[c][1] << ' ' << s.nt[c] << ' ' << p0[c] << ' ' << p[c]
                      << ' ' << raw0 << ' ' << raw1 << ' ' << r.flips[c][0] << ' ' << r.flips[c][1];
        }
        std::cout << '\n';
    }
}
