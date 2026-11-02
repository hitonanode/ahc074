    // Each sequence uses its own RNG, never shared with the oracle. The simulator does not read
    // the request tail of the input. Each policy starts at the identical initial stack.
    if (int ns = env_int("SIM_SEQS"); ns > 0) {
        const int requested_steps = env_int("SIM_STEPS");
        const int steps = requested_steps > 0 ? requested_steps : R;
        std::cout << std::setprecision(12);
        u64 hash = 1469598103934665603ULL;
        for (const auto& p : papers) hash = ((hash ^ p.opaque) * 1099511628211ULL ^ p.black) * 1099511628211ULL;
        std::cout << "{\"design_hash\":\"" << hash << "\",\"G\":" << G << "}" << std::endl;
        for (int q = 0; q < ns; q++) {
            Solver sim = solver;
            sim.oracle_samples = env_int("ORACLE_SAMPLES");
            const char* tw = std::getenv("TERMINAL_WEIGHT");
            if (tw) sim.terminal_weight = std::atof(tw);
            std::mt19937_64 rr(1000003ULL * (q + 1));
            int prev = rr() % P;
            Solver::Counts count;
            const double started = elapsed_sec();
            for (int t = 0; t < steps; t++) {
                int u = t == 0 ? prev : int(rr() % (P - 1));
                if (t > 0 && u >= prev) u++;
                prev = u;
                const auto before = sim.save();
                const auto path = sim.process(u);
                sim.account(before, path, u, count);
            }
            std::cout << "{\"sequence\":" << q << ",\"steps\":" << steps
                      << ",\"samples\":" << sim.oracle_samples << ",\"terminal_weight\":" << sim.terminal_weight
                      << ",\"total\":" << count.total << ",\"generic\":" << count.generic
                      << ",\"lift\":" << count.lift << ",\"old_top\":" << count.old_top
                      << ",\"old_filler\":" << count.old_filler << ",\"dig_d\":" << count.dig_d
                      << ",\"filler\":" << count.filler << ",\"fix\":" << count.fix
                      << ",\"wrong\":" << count.wrong << ",\"illegal\":" << count.illegal
                      << ",\"filler_state\":" << count.filler_state
                      << ",\"oracle_calls\":" << sim.oracle_calls << ",\"candidates\":" << sim.oracle_candidates
                      << ",\"changed\":" << sim.oracle_changed << ",\"oracle_bad\":" << sim.oracle_bad
                      << ",\"req_sec\":" << elapsed_sec()-started << "}" << std::endl;
        }
        return 0;
    }
