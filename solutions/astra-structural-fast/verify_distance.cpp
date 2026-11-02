// Research check: compare the directed-ball identity to an independent explicit
// minimum over all 720 initial states and thousands of goal subsets.
#define main solver_program_main
#include "main.cpp"
#undef main

int main() {
    Comparator c;
    std::mt19937_64 rr(673109);
    c.init(6, 36, rr);
    c.rebuild_truth();
    int checked = 0;
    for (int t = 0; t < 1200; ++t) {
        Comparator::StateBits bits{};
        int n = 1 + int(rr() % 100);
        for (int i = 0; i < n; ++i) {
            int g = rr() % 720;
            bits[g >> 6] |= 1ULL << (g & 63);
        }
        const auto goals = Comparator::enumerate(bits);
        int sum = 0;
        for (int s = 0; s < 720; ++s) {
            int best = 6;
            for (int g : goals) best = std::min(best, c.distance(s, g));
            sum += best;
        }
        double exact = double(sum) / 720;
        if (exact != c.exact_goal_mean(bits)) return 1;
        checked++;
    }
    std::cout << "directed_goal_distance_sets = " << checked << "\n";
    return 0;
}
