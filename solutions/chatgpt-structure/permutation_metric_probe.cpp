// Exhaustive diagnostic for the label-invariant legal permutation distance.
// This is a research executable, not the contest submission. The unmodified
// imp-gla Comparator supplies the independent all-sources BFS reference.
#define main imp_gla_reference_program_main
#include "../imp-gla/main.cpp"
#undef main

#include <stdexcept>

namespace permutation_probe {

struct RelativeTable {
    int m;
    std::vector<int> factorial;
    std::vector<std::vector<int>> orders;
    std::vector<unsigned char> distance_from_identity;
    std::vector<int> parent;
    std::vector<unsigned char> moved_label, insertion_depth;
    long long examined_edges = 0;

    explicit RelativeTable(int size) : m(size), factorial(size + 1, 1) {
        for (int i = 1; i <= m; ++i) factorial[i] = factorial[i - 1] * i;
        std::vector<int> p(m);
        std::iota(p.begin(), p.end(), 0);
        do orders.push_back(p); while (std::next_permutation(p.begin(), p.end()));
        const int count = orders.size();
        distance_from_identity.assign(count, 255);
        parent.assign(count, -1);
        moved_label.assign(count, 0);
        insertion_depth.assign(count, 0);
        std::vector<int> queue(count);
        int head = 0, tail = 0;
        queue[tail++] = 0;
        distance_from_identity[0] = 0;
        while (head < tail) {
            const int s = queue[head++];
            for (int position = 0; position < m - 1; ++position)
                for (int depth = 0; depth < m; ++depth) if (position != depth) {
                    auto q = orders[s];
                    const int label = q[position];
                    q.erase(q.begin() + position);
                    q.insert(q.begin() + depth, label);
                    const int t = rank(q);
                    ++examined_edges;
                    if (distance_from_identity[t] != 255) continue;
                    distance_from_identity[t] = distance_from_identity[s] + 1;
                    parent[t] = s;
                    moved_label[t] = label;
                    insertion_depth[t] = depth;
                    queue[tail++] = t;
                }
        }
        if (tail != count) throw std::runtime_error("legal graph is not fully reached");
    }

    // Lexicographic permutation rank, matching Comparator::perms exactly.
    int rank(const std::vector<int>& p) const {
        unsigned used = 0;
        int r = 0;
        for (int i = 0; i < m; ++i) {
            const unsigned smaller_unused = ((1U << p[i]) - 1) & ~used;
            r += __builtin_popcount(smaller_unused) * factorial[m - 1 - i];
            used |= 1U << p[i];
        }
        return r;
    }

    int relative_rank(const std::vector<int>& from, const std::vector<int>& to) const {
        std::vector<int> inverse(m), relative(m);
        for (int i = 0; i < m; ++i) inverse[from[i]] = i;
        for (int i = 0; i < m; ++i) relative[i] = inverse[to[i]];
        return rank(relative);
    }

    int distance(const std::vector<int>& from, const std::vector<int>& to) const {
        return distance_from_identity[relative_rank(from, to)];
    }

    // A source order p relabels the identity's label i as paper p[i].
    // Relabeling leaves positions, insertion depths, and bottom visibility
    // unchanged, so the identity BFS path translates into a legal shortest path.
    std::vector<std::pair<int, int>> path(const std::vector<int>& from,
                                         const std::vector<int>& to) const {
        std::vector<std::pair<int, int>> moves;
        for (int t = relative_rank(from, to); t; t = parent[t])
            moves.emplace_back(from[moved_label[t]], insertion_depth[t]);
        std::reverse(moves.begin(), moves.end());
        return moves;
    }
};

void verify_path(const RelativeTable& table, const std::vector<int>& from,
                 const std::vector<int>& to, int expected) {
    auto current = from;
    const auto moves = table.path(from, to);
    if (int(moves.size()) != expected) throw std::runtime_error("path length mismatch");
    for (auto [paper, depth] : moves) {
        const int position = std::find(current.begin(), current.end(), paper) - current.begin();
        if (position >= table.m - 1) throw std::runtime_error("path moves hidden bottom paper");
        if (depth < 0 || depth >= table.m) throw std::runtime_error("invalid insertion depth");
        current.erase(current.begin() + position);
        current.insert(current.begin() + depth, paper);
    }
    if (current != to) throw std::runtime_error("path endpoint mismatch");
}

}  // namespace permutation_probe

int main() {
    using namespace permutation_probe;
    try {
        long long pair_checks = 0;
        std::cout << "{\n  \"reference\": \"solutions/imp-gla/main.cpp Comparator::build_tables\",\n"
                  << "  \"assumption\": \"every non-bottom paper is visible; the bottom paper is not\",\n"
                  << "  \"exhaustive_checks\": [\n";
        for (int m = 2; m <= 6; ++m) {
            Comparator reference;
            std::mt19937_64 rng(1234567);
            reference.init(m, m * (m - 1) / 2, rng);
            reference.build_tables();
            RelativeTable table(m);
            if (table.orders != reference.perms) throw std::runtime_error("permutation order mismatch");
            const int count = table.orders.size();
            for (int a = 0; a < count; ++a) for (int b = 0; b < count; ++b) {
                const int expected = reference.distance(a, b);
                if (table.distance(table.orders[a], table.orders[b]) != expected)
                    throw std::runtime_error("distance mismatch against all-sources BFS");
                verify_path(table, table.orders[a], table.orders[b], expected);
                ++pair_checks;
            }
            std::cout << "    {\"M\": " << m << ", \"states\": " << count
                      << ", \"distance_and_path_pairs\": " << (long long)count * count
                      << ", \"single_bfs_edges\": " << table.examined_edges
                      << ", \"distance_bytes\": " << table.distance_from_identity.size()
                      << ", \"reference_distance_bytes\": " << reference.dist.size()
                      << ", \"passed\": true}" << (m == 6 ? "\n" : ",\n");
        }
        std::cout << "  ],\n  \"large_tables\": [\n";
        for (int m : {7, 8}) {
            RelativeTable table(m);
            const int count = table.orders.size();
            // Check every identity-to-goal path at the larger state counts too.
            for (int b = 0; b < count; ++b)
                verify_path(table, table.orders[0], table.orders[b], table.distance_from_identity[b]);
            std::cout << "    {\"M\": " << m << ", \"states\": " << count
                      << ", \"single_bfs_edges\": " << table.examined_edges
                      << ", \"distance_bytes\": " << table.distance_from_identity.size()
                      << ", \"dense_distance_bytes_if_stored\": " << (long long)count * count
                      << ", \"parent_bytes\": " << table.parent.size() * sizeof(int)
                      << ", \"move_bytes\": " << table.moved_label.size() + table.insertion_depth.size()
                      << ", \"identity_paths_checked\": " << count
                      << ", \"passed\": true}" << (m == 8 ? "\n" : ",\n");
        }
        std::cout << "  ],\n  \"total_all_pairs_checks\": " << pair_checks
                  << ",\n  \"all_passed\": true\n}\n";
    } catch (const std::exception& e) {
        std::cerr << "verification failed: " << e.what() << '\n';
        return 1;
    }
}
