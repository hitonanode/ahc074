// Check the new integer SIMD costs against the original scalar formula.
#define main solver_main
#include "main.cpp"
#undef main

__attribute__((target("avx2,fma,bmi,bmi2,popcnt"))) int verify() {
    std::uint64_t checked = 0;
    for (int n = 0; n <= 186; ++n) {
        for (int pairs = 0; pairs <= std::min(n, 256-n); ++pairs) {
            // p1 only affects the formula by being 0, pairs, or neither.
            for (int p1 : {0, pairs, pairs/2}) {
                for (int first = 0; first <= n; first += 4) {
                    alignas(16) int ones[4], got[4];
                    for (int i = 0; i < 4; ++i) ones[i] = std::min(n,first+i);
                    const auto result = Design::Annealer<4>::colcost_pair(
                        _mm_set1_epi32(n), _mm_set1_epi32(n+pairs),
                        _mm_load_si128((const __m128i*)ones), _mm_set1_epi32(p1));
                    _mm_store_si128((__m128i*)got,result);
                    for (int i = 0; i < 4; ++i) {
                        const int want = Design::colcost40(n,n+pairs,ones[i],p1);
                        if (got[i] != want) { std::cerr << "Mismatch " << n << ' ' << pairs << ' ' << ones[i] << ' ' << p1 << '\n'; return 1; }
                        ++checked;
                    }
                }
            }
        }
    }
    std::cout << "colcost_lanes_checked = " << checked << "\nmismatches = 0\n";
    return 0;
}
int main() { return verify(); }
