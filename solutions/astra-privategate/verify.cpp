// Focused structural verification; not an AtCoder submission.
#define main privategate_solver_main
#include "main.cpp"
#undef main

int main() {
    Comparator c;
    std::mt19937_64 rng(0x754aae19ULL);
    c.init(6, 36, rng);
    int private_window = -1;
    for (int j = 0; j < 36; ++j)
        if (c.edge[j].first == 0 || c.edge[j].second == 0) { private_window = j; break; }
    assert(private_window >= 0);
    c.private_window = private_window;
    const u64 bit = 1ULL << private_window;
    for (int k = 0; k < 6; ++k) c.opq[k] &= ~bit, c.black[k] &= ~bit;
    c.opq[0] |= bit;
    c.nonlinear = true;
    c.rebuild_truth();

    long long checked_edges = 0, bottom_edges = 0, checked_goals = 0;
    for (int stage = 0; stage < 2; ++stage) {
        if (stage) c.use_final_visibility_graph();
        assert(c.safe_diameter <= 5);
        for (int s = 0; s < 720; ++s) {
            assert(!(c.actual_display[s] & bit));
            u64 covered = 0;
            for (int pos = 0; pos < 6; ++pos) {
                const int paper = c.perms[s][pos];
                const bool visible = (c.opq[paper] & ~covered) != 0;
                for (int d = 0; d < 6; ++d) {
                    const int t = c.next[s][pos * 6 + d];
                    if (t < 0) continue;
                    assert(visible);
                    auto direct = c.perms[s];
                    direct.erase(direct.begin() + pos);
                    direct.insert(direct.begin() + d, paper);
                    assert(direct == c.perms[t]);
                    checked_edges++;
                    if (pos == 5 && paper == 0) bottom_edges++;
                }
                covered |= c.opq[paper];
            }
        }
        assert(!Comparator::any(c.truth[private_window][1]));
        for (std::uint8_t d : c.dist) assert(d <= 5);
        for (int rep = 0; rep < 600; ++rep) {
            Comparator::StateBits goals{};
            const int wanted = 1 + int(rng() % 16);
            for (int i = 0; i < wanted; ++i) {
                const int state = int(rng() % 720);
                goals[state >> 6] |= 1ULL << (state & 63);
            }
            const auto ids = Comparator::enumerate(goals);
            int direct_sum = 0;
            for (int s = 0; s < 720; ++s) {
                int best = 255;
                for (int g : ids) best = std::min(best, c.distance(s, g));
                direct_sum += best;
            }
            assert(std::abs(c.exact_goal_mean(goals) - direct_sum / 720.0) < 1e-12);
            checked_goals++;
        }
    }
    assert(bottom_edges == 1200); // 120 bottom states * 5 destinations * 2 graphs
    std::cout << "legal_edges=" << checked_edges << " bottom_private_edges=" << bottom_edges
              << " exact_goal_sets=" << checked_goals << " failures=0\n";
}
