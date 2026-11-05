from pathlib import Path
here=Path(__file__).resolve().parent
s=(here.parent/'argon-des-perf-latew105/main.cpp').read_text()
needle='    // ==== Solver: future-cost model of the stack ===='
helper='''    // The lexicographic rank of the six generic sheets, including interleaved helpers.
    // future is conditional on a target having generic holes; the new coefficient is absolute.
    inline static long long d4_value_calls = 0;
    inline static double d4_final_future_sum = 0;
    __attribute__((target("popcnt"))) double d4_generic_future(const std::array<uint8_t, K>& stack) const {
        ++d4_value_calls;
        if (future.empty()) return 0;
        int rank = 0, left = M;
        unsigned used = 0;
        for (int k : stack) if (k < M) {
            rank = rank * left + k - __builtin_popcount(used & ((1U << k) - 1));
            used |= 1U << k;
            if (!--left) break;
        }
        assert(left == 0 && rank < int(future.size()));
        return future[rank];
    }
    double d4_generic_term() const {
        static const double weight = env_real("ARGON_D4_WEIGHT", 0.1);
        return weight ? weight * d4_generic_future(order) : 0;
    }

'''
assert s.count(needle)==1;s=s.replace(needle,helper+needle)
s=s.replace('return moves + filler_charge(split) + kEndWeight * adaptive_next_cost(split);','return moves + filler_charge(split) + kEndWeight * adaptive_next_cost(split) + d4_generic_term();')
s=s.replace('memo->next_cost = kEndWeight * adaptive_next_cost(split);','memo->next_cost = kEndWeight * adaptive_next_cost(split) + d4_generic_term();')
s=s.replace('        post_secondary_saved += original_length - int(chosen_path.size());','        d4_final_future_sum += d4_generic_future(order);\n        post_secondary_saved += original_length - int(chosen_path.size());')
s=s.replace('    // ==== main: statistics ====','''    // ==== main: statistics ====
    std::cerr << "d4_value_calls = " << solver.d4_value_calls
              << "\\nd4_final_future = " << solver.d4_final_future_sum / R << '\\n';''')
(here/'main.cpp').write_text(s)
