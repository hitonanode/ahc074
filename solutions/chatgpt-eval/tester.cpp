// Local C++ port of tools/src/lib.rs interaction/state and bin/tester.rs verdict.
// This is an evaluation utility, not a submitted solver.
#include <algorithm>
#include <cerrno>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

struct Reader {
    FILE* source;
    std::istringstream line;
    bool next(std::string& s) {
        while (!(line >> s)) {
            char* data = nullptr;
            std::size_t capacity = 0;
            const ssize_t n = getline(&data, &capacity, source);
            if (n < 0) { std::free(data); return false; }
            if (std::fwrite(data, 1, static_cast<std::size_t>(n), stdout) != static_cast<std::size_t>(n)) {
                std::free(data);
                throw std::runtime_error("Tester stdout relay write failed");
            }
            line.clear();
            line.str(std::string(data, static_cast<std::size_t>(n)));
            std::free(data);
        }
        return true;
    }
    std::string token() {
        std::string s;
        if (!next(s)) throw std::runtime_error("Unexpected EOF");
        return s;
    }
    int integer(int hi) {
        const std::string s = token();
        // Rust's usize parser rejects a minus sign even for "-0".
        if (!s.empty() && s[0] == '-') throw std::runtime_error("Parse error: " + s);
        std::size_t used = 0;
        long long x;
        try { x = std::stoll(s, &used); }
        catch (...) { throw std::runtime_error("Parse error: " + s); }
        if (used != s.size()) throw std::runtime_error("Parse error: " + s);
        if (x < 0 || x > hi) throw std::runtime_error("Out of range: " + s);
        return static_cast<int>(x);
    }
};

std::uint64_t mask(const std::string& s, char color) {
    std::uint64_t v = 0;
    for (std::size_t i = 0; i < s.size(); ++i) if (s[i] == color) v |= UINT64_C(1) << i;
    return v;
}

int main(int argc, char** argv) {
    if (argc < 2) { std::cerr << "Usage: tester <command> [args...]\n"; return 1; }
    std::signal(SIGPIPE, SIG_IGN);
    int N, K, P, R;
    if (!(std::cin >> N >> K >> P >> R) || N < 1 || N > 64 || K < 1 || P < 1 || R < 1) {
        std::cerr << "Invalid tester input\nScore = 0\n"; return 1;
    }
    std::vector<std::string> A(P);
    std::vector<int> requests(R);
    for (auto& a : A) std::cin >> a;
    for (auto& a : requests) std::cin >> a;
    if (!std::cin) { std::cerr << "Truncated tester input\nScore = 0\n"; return 1; }
    for (const auto& a : A) if (static_cast<int>(a.size()) != N) return 1;
    for (const int a : requests) if (a < 0 || a >= P) return 1;
    int input_fd[2], output_fd[2];
    if (pipe(input_fd) || pipe(output_fd)) return 1;
    const pid_t child = fork();
    if (child < 0) return 1;
    if (child == 0) {
        dup2(input_fd[0], STDIN_FILENO);
        dup2(output_fd[1], STDOUT_FILENO);
        close(input_fd[0]); close(input_fd[1]);
        close(output_fd[0]); close(output_fd[1]);
        execvp(argv[1], argv + 1);
        std::fprintf(stderr, "failed to execute the command: %s\n", std::strerror(errno));
        _exit(127);
    }
    close(input_fd[0]); close(output_fd[1]);
    FILE* sink = fdopen(input_fd[1], "w");
    FILE* source = fdopen(output_fd[0], "r");
    Reader reader{source, std::istringstream()};
    std::vector<std::uint64_t> opaque(K), black(K);
    std::vector<int> order(K);
    std::iota(order.begin(), order.end(), 0);
    long long moves = 0, mistakes = 0;
    std::string error;
    std::fprintf(sink, "%d %d %d %d\n", N, K, P, R);
    for (const auto& a : A) std::fprintf(sink, "%s\n", a.c_str());
    std::fflush(sink);
    try {
        for (int k = 0; k < K; ++k) {
            const auto s = reader.token();
            if (static_cast<int>(s.size()) != N || s.find_first_not_of("01.") != std::string::npos)
                throw std::runtime_error("Expected a paper pattern of length N using 0, 1, .");
            opaque[k] = mask(s, '0') | mask(s, '1'); black[k] = mask(s, '1');
        }
        for (int r = 0; r < R; ++r) {
            std::fprintf(sink, "%d\n", requests[r]); std::fflush(sink);
            const int count = reader.integer(2 * K);
            for (int t = 0; t < count; ++t) {
                const int k = reader.integer(K - 1), d = reader.integer(K - 1);
                std::uint64_t exposed = opaque[k];
                int pos = 0;
                while (exposed && order[pos] != k) exposed &= ~opaque[order[pos++]];
                if (!exposed) throw std::runtime_error("Paper " + std::to_string(k) + " is not visible");
                order.erase(order.begin() + pos); order.insert(order.begin() + d, k); ++moves;
            }
            std::uint64_t covered = 0, shown = 0;
            for (const int k : order) { shown |= black[k] & ~covered; covered |= opaque[k]; }
            if (shown != mask(A[requests[r]], '1')) ++mistakes;
        }
        // Close solver stdin before waiting for final EOF, as the Rust tester does.
        std::fclose(sink); sink = nullptr;
        std::string extra;
        while (reader.next(extra)) error = "Extra output after the last turn";
    } catch (const std::exception& e) { error = e.what(); }
    if (sink) { std::fprintf(sink, "-1\n"); std::fflush(sink); std::fclose(sink); }
    std::fclose(source);
    if (std::fflush(stdout) != 0) error = "Tester stdout relay flush failed";
    // Persist complete logs before the driver reads them. fsync is only valid
    // for ordinary output files; diagnostic fixtures also use pipes.
    struct stat output_stat{};
    if (fstat(STDOUT_FILENO, &output_stat) == 0 && S_ISREG(output_stat.st_mode))
        if (fsync(STDOUT_FILENO) != 0) error = "Tester stdout relay sync failed";
    int status = 0;
    if (!error.empty()) kill(child, SIGKILL);
    while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    if (error.empty() && (!WIFEXITED(status) || WEXITSTATUS(status) != 0))
        error = "Your program terminated abnormally";
    if (!error.empty()) std::cerr << error << "\nScore = 0\n";
    else std::cerr << "Score = " << 2LL * K * mistakes + moves << '\n';
    std::cerr.flush();
    struct stat error_stat{};
    if (fstat(STDERR_FILENO, &error_stat) == 0 && S_ISREG(error_stat.st_mode)) fsync(STDERR_FILENO);
    return 0;
}
