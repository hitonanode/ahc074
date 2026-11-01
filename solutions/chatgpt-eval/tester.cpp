// Portable local interactor for AHC074. This is an independently implemented
// adapter, not the official Rust tester. See README.md for validation and limits.
#include <algorithm>
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <deque>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

struct Plate {
    std::uint64_t opaque = 0, black = 0;
};

class Receiver {
    FILE* input;
    char* line = nullptr;
    std::size_t capacity = 0;
    std::deque<std::string> pending;
public:
    explicit Receiver(FILE* f) : input(f) {}
    ~Receiver() { std::free(line); }
    bool next(std::string& out) {
        while (pending.empty()) {
            const ssize_t n = getline(&line, &capacity, input);
            if (n < 0) return false;
            // Relay the original bytes, as the official tester does.
            std::fwrite(line, 1, static_cast<std::size_t>(n), stdout);
            std::istringstream stream(std::string(line, static_cast<std::size_t>(n)));
            std::string token;
            while (stream >> token) pending.push_back(std::move(token));
        }
        out = std::move(pending.front());
        pending.pop_front();
        return true;
    }
    std::string take() {
        std::string s;
        if (!next(s)) throw std::runtime_error("Unexpected EOF");
        return s;
    }
    int number(int upper) {
        const std::string s = take();
        std::size_t pos = !s.empty() && s[0] == '+' ? 1 : 0;
        if (pos == s.size()) throw std::runtime_error("Parse error: " + s);
        unsigned long long value = 0;
        for (; pos < s.size(); ++pos) {
            if (s[pos] < '0' || s[pos] > '9')
                throw std::runtime_error("Parse error: " + s.substr(0, 40));
            if (value > 1000000ULL) throw std::runtime_error("Out of range: " + s.substr(0, 40));
            value = 10 * value + static_cast<unsigned>(s[pos] - '0');
        }
        if (value > static_cast<unsigned>(upper))
            throw std::runtime_error("Out of range: " + s.substr(0, 40));
        return static_cast<int>(value);
    }
};

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "Usage: %s <solver> [args...]\n", argv[0]);
        return 1;
    }
    std::signal(SIGPIPE, SIG_IGN);
    int n, k, p, r;
    if (!(std::cin >> n >> k >> p >> r) || n < 1 || n > 64 || k < 1 || p < 1 || r < 0) {
        std::fprintf(stderr, "Invalid test input\nScore = 0\n");
        return 1;
    }
    std::vector<std::string> patterns(p);
    std::vector<std::uint64_t> targets(p, 0);
    for (int i = 0; i < p; ++i) {
        std::cin >> patterns[i];
        if (static_cast<int>(patterns[i].size()) != n) return 1;
        for (int j = 0; j < n; ++j)
            if (patterns[i][j] == '1') targets[i] |= std::uint64_t(1) << j;
    }
    std::vector<int> requests(r);
    for (int& x : requests) {
        if (!(std::cin >> x) || x < 0 || x >= p) return 1;
    }
    int to_child[2], from_child[2];
    if (pipe(to_child) || pipe(from_child)) return 1;
    const pid_t child = fork();
    if (child < 0) return 1;
    if (child == 0) {
        dup2(to_child[0], STDIN_FILENO);
        dup2(from_child[1], STDOUT_FILENO);
        close(to_child[0]); close(to_child[1]);
        close(from_child[0]); close(from_child[1]);
        execvp(argv[1], argv + 1);
        std::perror("execvp");
        _exit(127);
    }
    close(to_child[0]); close(from_child[1]);
    FILE* writer = fdopen(to_child[1], "w");
    FILE* reader = fdopen(from_child[0], "r");
    std::setvbuf(stdout, nullptr, _IOFBF, 65536);
    std::fprintf(writer, "%d %d %d %d\n", n, k, p, r);
    for (const auto& s : patterns) std::fprintf(writer, "%s\n", s.c_str());
    std::fflush(writer);

    Receiver receive(reader);
    std::vector<Plate> plates(k);
    std::vector<int> order(k);
    std::iota(order.begin(), order.end(), 0);
    long long moves = 0, mistakes = 0;
    std::string error;
    try {
        for (int i = 0; i < k; ++i) {
            const auto s = receive.take();
            if (static_cast<int>(s.size()) != n || s.find_first_not_of("01.") != std::string::npos)
                throw std::runtime_error("Expected a paper pattern of length N using 0, 1, .");
            for (int j = 0; j < n; ++j) {
                if (s[j] != '.') plates[i].opaque |= std::uint64_t(1) << j;
                if (s[j] == '1') plates[i].black |= std::uint64_t(1) << j;
            }
        }
        for (int q = 0; q < r; ++q) {
            // The next request is released only after all previous operations
            // have been checked; hidden future requests never reach the solver.
            std::fprintf(writer, "%d\n", requests[q]);
            std::fflush(writer);
            const int count = receive.number(2 * k);
            for (int z = 0; z < count; ++z) {
                const int paper = receive.number(k - 1), depth = receive.number(k - 1);
                auto found = std::find(order.begin(), order.end(), paper);
                std::uint64_t covered = 0;
                for (auto it = order.begin(); it != found; ++it) covered |= plates[*it].opaque;
                if (!(plates[paper].opaque & ~covered))
                    throw std::runtime_error("Paper " + std::to_string(paper) + " is not visible");
                order.erase(found);
                order.insert(order.begin() + depth, paper);
                ++moves;
            }
            std::uint64_t covered = 0, black = 0;
            for (int paper : order) {
                black |= plates[paper].black & ~covered;
                covered |= plates[paper].opaque;
            }
            mistakes += black != targets[requests[q]];
        }
        // The official protocol has no acknowledgement of the last request.
        std::fclose(writer);
        writer = nullptr;
        std::string extra;
        if (receive.next(extra)) throw std::runtime_error("Extra output after the last turn");
    } catch (const std::exception& e) {
        error = e.what();
        if (writer) {
            std::fputs("-1\n", writer);
            std::fflush(writer);
        }
    }
    if (writer) std::fclose(writer);
    int status = 0;
    if (!error.empty()) {
        // Invalid output must not leave a solver waiting forever for a request.
        for (int i = 0; i < 10; ++i) {
            if (waitpid(child, &status, WNOHANG) == child) break;
            if (i == 9) { kill(child, SIGKILL); waitpid(child, &status, 0); }
            else usleep(1000);
        }
    } else {
        while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
        if (!WIFEXITED(status) || WEXITSTATUS(status) != 0)
            error = "Your program terminated abnormally";
    }
    std::fclose(reader);
    std::fflush(stdout);
    if (!error.empty()) std::fprintf(stderr, "%s\nScore = 0\n", error.c_str());
    else std::fprintf(stderr, "adapter_mistakes = %lld\nadapter_moves = %lld\nScore = %lld\n",
                      mistakes, moves, 2LL * k * mistakes + moves);
    return error.empty() ? 0 : 1;
}
