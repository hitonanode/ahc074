#include "common.hpp"
#include "../anchor-match/matching.hpp"
#include "../head-prob/prob.hpp"

struct Candidate {
    std::unique_ptr<Design> design;
    double raw = 0, merit = 0, seconds = 0;
};

int main(int argc, char** argv) {
    if (argc < 3) return 2;
    auto base = head::load(argv[1], argv[2]);
    if (!base) return 3;
    auto initial = recover(*base);
    const int sequences = argc > 3 ? std::stoi(argv[3]) : 16;
    std::vector<Candidate> candidates;
    std::vector<int> selected;
    for (int count : {1, 2, 4}) {
        const int begin = candidates.size();
        for (int k = 0; k < count; k++) {
            auto d = std::make_unique<Design>(*initial);
            d->rng.x ^= 0x7c317d9b51ULL * k;
            const double start = elapsed_sec();
            d->anneal(1e9, 20000000 / count);
            d->refresh_reset();
            const double raw = d->cur;
            d->filler_climb(1e9, 65000);
            rematch_probability(*d, 4, 1, 2, true, true);
            d->refresh_reset();
            ProbabilityHead h(*d, 2, true);
            const double merit = d->cur - h.rebuild();
            candidates.push_back({std::move(d), raw, merit, elapsed_sec() - start});
        }
        int raw_best = begin, head_best = begin;
        for (int j = begin + 1; j < int(candidates.size()); j++) {
            if (candidates[j].raw < candidates[raw_best].raw) raw_best = j;
            if (candidates[j].merit < candidates[head_best].merit) head_best = j;
        }
        selected.push_back(raw_best);
        if (count > 1) selected.push_back(head_best);
    }
    double reference = 0;
    std::cout << std::setprecision(12) << "[";
    for (int mode = 0; mode < int(selected.size()); mode++) {
        auto& c = candidates[selected[mode]];
        Solver s = *base;
        materialize(s, *c.design);
        auto state = s.save();
        long long total = 0, wrong = 0;
        for (int q = 0; q < sequences; q++) {
            s.restore(state);
            std::mt19937_64 rng(331000003ULL * (q + 1));
            int prev = rng() % P;
            for (int t = 0; t < 1024; t++) {
                int u = t ? int(rng() % (P - 1)) : prev;
                if (t && u >= prev) u++;
                prev = u;
                auto before = s.order;
                auto path = s.process(u);
                total += path.size();
                wrong += s.display() != s.A[u];
                if (q == 0) {
                    for (auto [k, depth] : path) {
                        int at = std::find(before.begin(), before.end(), k) - before.begin();
                        u64 covered = 0;
                        for (int j = 0; j < at; j++) covered |= s.paper[before[j]].opaque;
                        assert(s.paper[k].opaque & ~covered);
                        before.erase(before.begin() + at);
                        before.insert(before.begin() + depth, k);
                    }
                    assert(before == s.order);
                }
            }
        }
        assert(!wrong);
        const double average = double(total) / (sequences * 1024);
        if (!mode) reference = average;
        std::cout << (mode ? "," : "") << "{\"mode\":" << mode
                  << ",\"chosen\":" << selected[mode] << ",\"moves\":" << average
                  << ",\"difference\":" << average - reference << ",\"wrong\":" << wrong
                  << ",\"raw\":" << c.raw / P << ",\"merit\":" << c.merit / P
                  << ",\"seconds\":" << c.seconds << "}" << std::flush;
    }
    std::cout << "]\n";
}
