// Portable interactive judge for the exact rules in tools/src/lib.rs.
// Used only when the official Rust tester is unavailable. Not a solution.
#include <algorithm>
#include <cerrno>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

using U64 = std::uint64_t;
struct Paper { U64 opaque = 0, black = 0; };

int main(int argc, char** argv) {
    if (argc < 2) return 2;
    std::signal(SIGPIPE, SIG_IGN);
    int N, K, P, R;
    if (!(std::cin >> N >> K >> P >> R)) return 2;
    if (N < 1 || N > 64 || K < 1 || P < 1 || R < 1) return 2;
    std::vector<std::string> patterns(P);
    std::vector<U64> targets(P);
    for (int a = 0; a < P; ++a) {
        std::cin >> patterns[a];
        if (int(patterns[a].size()) != N) return 2;
        for (int j = 0; j < N; ++j) if (patterns[a][j] == '1') targets[a] |= U64(1) << j;
    }
    std::vector<int> requests(R);
    for (int& a : requests) { std::cin >> a; if (a < 0 || a >= P) return 2; }
    int to_child[2], from_child[2];
    if (pipe(to_child) || pipe(from_child)) return 2;
    pid_t pid = fork();
    if (pid == -1) return 2;
    if (pid == 0) {
        dup2(to_child[0], STDIN_FILENO);
        dup2(from_child[1], STDOUT_FILENO);
        close(to_child[0]); close(to_child[1]); close(from_child[0]); close(from_child[1]);
        execvp(argv[1], argv + 1);
        _exit(127);
    }
    close(to_child[0]); close(from_child[1]);
    FILE* send = fdopen(to_child[1], "w");
    FILE* receive = fdopen(from_child[0], "r");
    std::vector<Paper> papers(K);
    std::vector<int> order(K);
    std::iota(order.begin(), order.end(), 0);
    long long total = 0, errors = 0;
    int status = 0;
    auto token = [&]() {
        char buf[4096];
        if (fscanf(receive, "%4095s", buf) != 1) throw std::runtime_error("Unexpected EOF");
        return std::string(buf);
    };
    auto number = [&](int lo, int hi) {
        const std::string s = token();
        char* end = nullptr;
        errno = 0;
        long x = strtol(s.c_str(), &end, 10);
        if (errno || end != s.c_str() + s.size() || end == s.c_str() || x < lo || x > hi)
            throw std::runtime_error("Invalid integer: " + s);
        return int(x);
    };
    try {
        fprintf(send, "%d %d %d %d\n", N, K, P, R);
        for (const auto& s : patterns) fprintf(send, "%s\n", s.c_str());
        fflush(send);
        for (auto& p : papers) {
            auto s = token();
            if (int(s.size()) != N || s.find_first_not_of("01.") != std::string::npos)
                throw std::runtime_error("Invalid paper pattern");
            for (int j = 0; j < N; ++j) {
                if (s[j] != '.') p.opaque |= U64(1) << j;
                if (s[j] == '1') p.black |= U64(1) << j;
            }
            printf("%s\n", s.c_str());
        }
        for (int r = 0; r < R; ++r) {
            fprintf(send, "%d\n", requests[r]); fflush(send);
            const int count = number(0, 2 * K);
            printf("%d\n", count);
            for (int i = 0; i < count; ++i) {
                const int k = number(0, K - 1), d = number(0, K - 1);
                U64 exposed = papers[k].opaque;
                int pos = 0;
                while (order[pos] != k) { exposed &= ~papers[order[pos]].opaque; ++pos; }
                if (!exposed) throw std::runtime_error("Paper " + std::to_string(k) + " is not visible");
                if (pos < d) std::rotate(order.begin() + pos, order.begin() + pos + 1, order.begin() + d + 1);
                else std::rotate(order.begin() + d, order.begin() + pos, order.begin() + pos + 1);
                ++total;
                printf("%d %d\n", k, d);
            }
            U64 covered = 0, black = 0;
            for (int k : order) { black |= papers[k].black & ~covered; covered |= papers[k].opaque; }
            errors += black != targets[requests[r]];
        }
        fclose(send); send = nullptr;
        char extra[2];
        if (fscanf(receive, "%1s", extra) == 1) throw std::runtime_error("Extra output after the last turn");
        fclose(receive); receive = nullptr;
        waitpid(pid, &status, 0);
        if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) throw std::runtime_error("Solver terminated abnormally");
        fprintf(stderr, "portable_judge_errors = %lld\nScore = %lld\n", errors, 2LL * K * errors + total);
    } catch (const std::exception& e) {
        if (send) { fprintf(send, "-1\n"); fflush(send); fclose(send); }
        kill(pid, SIGKILL);
        waitpid(pid, &status, 0);
        if (receive) fclose(receive);
        fprintf(stderr, "%s\nScore = 0\n", e.what());
        return 1;
    }
    return 0;
}
