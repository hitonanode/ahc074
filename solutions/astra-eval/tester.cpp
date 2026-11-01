// AHC074 local tester port. Source semantics: tools/src/lib.rs and bin/tester.rs.
// This is not the official Rust binary. Valid outputs are independently replayed.
#include <algorithm>
#include <cerrno>
#include <charconv>
#include <cctype>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

struct Input {
    int n, k, p, r;
    std::vector<std::string> a;
    std::vector<int> requests;
};
struct Plate { uint64_t opaque = 0, black = 0; };

class Reader {
    FILE* stream;
    char* line = nullptr;
    size_t capacity = 0;
    std::string current;
    size_t pos = 0;
public:
    explicit Reader(FILE* s): stream(s) {}
    ~Reader() { std::free(line); }
    bool next(std::string& token) {
        for (;;) {
            while (pos < current.size() && std::isspace(static_cast<unsigned char>(current[pos]))) ++pos;
            if (pos < current.size()) {
                const size_t start = pos;
                while (pos < current.size() && !std::isspace(static_cast<unsigned char>(current[pos]))) ++pos;
                token.assign(current, start, pos - start);
                return true;
            }
            const ssize_t count = getline(&line, &capacity, stream);
            if (count < 0) {
                if (std::ferror(stream)) throw std::runtime_error("Your program has terminated unexpectedly");
                return false;
            }
            // Relay every byte, as the official tester does, including invalid output.
            if (std::fwrite(line, 1, static_cast<size_t>(count), stdout) != static_cast<size_t>(count))
                throw std::runtime_error("Could not relay solver output");
            current.assign(line, static_cast<size_t>(count));
            pos = 0;
        }
    }
    std::string need() {
        std::string token;
        if (!next(token)) throw std::runtime_error("Unexpected EOF");
        return token;
    }
    int integer(int lo, int hi) {
        std::string token = need();
        std::string_view view(token);
        if (!view.empty() && view.front() == '+') view.remove_prefix(1);
        uint64_t value = 0;
        auto [end, ec] = std::from_chars(view.data(), view.data()+view.size(), value);
        if (ec != std::errc() || end != view.data()+view.size() || view.empty())
            throw std::runtime_error("Parse error: " + token.substr(0, 40));
        if (value < static_cast<uint64_t>(lo) || value > static_cast<uint64_t>(hi))
            throw std::runtime_error("Out of range: " + token);
        return static_cast<int>(value);
    }
};

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "Usage: %s <command> [args...]\n", argv[0]); return 1; }
    std::signal(SIGPIPE, SIG_IGN);
    Input in;
    if (!(std::cin >> in.n >> in.k >> in.p >> in.r) || in.n < 1 || in.n > 64 || in.k < 1)
        { std::fprintf(stderr,"Invalid tester input\nScore = 0\n"); return 1; }
    in.a.resize(in.p);
    in.requests.resize(in.r);
    for (auto& s: in.a) std::cin >> s;
    for (auto& a: in.requests) std::cin >> a;
    if (!std::cin) { std::fprintf(stderr,"Invalid tester input\nScore = 0\n"); return 1; }
    int to_child[2], from_child[2];
    if (pipe(to_child) || pipe(from_child)) { std::perror("pipe"); return 1; }
    const pid_t pid = fork();
    if (pid < 0) { std::perror("fork"); return 1; }
    if (pid == 0) {
        dup2(to_child[0], STDIN_FILENO);
        dup2(from_child[1], STDOUT_FILENO);
        close(to_child[0]); close(to_child[1]); close(from_child[0]); close(from_child[1]);
        execvp(argv[1], argv+1);
        std::perror("failed to execute the command");
        _exit(127);
    }
    close(to_child[0]); close(from_child[1]);
    FILE* child_in = fdopen(to_child[1], "w");
    FILE* child_out = fdopen(from_child[0], "r");
    if (!child_in || !child_out) { kill(pid, SIGKILL); waitpid(pid,nullptr,0); return 1; }
    Reader reader(child_out);
    std::string error;
    long long moves = 0, mistakes = 0;
    std::vector<Plate> plates(in.k);
    std::vector<int> order(in.k);
    std::iota(order.begin(), order.end(), 0);
    try {
        std::fprintf(child_in, "%d %d %d %d\n", in.n, in.k, in.p, in.r);
        for (const auto& a: in.a) std::fprintf(child_in, "%s\n", a.c_str());
        std::fflush(child_in);
        for (auto& plate: plates) {
            const std::string s = reader.need();
            if (static_cast<int>(s.size()) != in.n || s.find_first_not_of("01.") != std::string::npos)
                throw std::runtime_error("Expected a paper pattern of length N using 0, 1, .");
            for (int j = 0; j < in.n; ++j) {
                if (s[j] != '.') plate.opaque |= uint64_t(1) << j;
                if (s[j] == '1') plate.black |= uint64_t(1) << j;
            }
        }
        for (int r = 0; r < in.r; ++r) {
            // Future requests remain private until all actions of this turn are processed.
            std::fprintf(child_in, "%d\n", in.requests[r]);
            std::fflush(child_in);
            const int count = reader.integer(0, 2*in.k);
            for (int t = 0; t < count; ++t) {
                const int k = reader.integer(0, in.k-1), d = reader.integer(0, in.k-1);
                uint64_t exposed = plates[k].opaque;
                int pos = 0;
                while (pos < in.k && order[pos] != k) { exposed &= ~plates[order[pos]].opaque; ++pos; }
                if (exposed == 0) throw std::runtime_error("Paper " + std::to_string(k) + " is not visible");
                if (pos < d) std::rotate(order.begin()+pos, order.begin()+pos+1, order.begin()+d+1);
                else std::rotate(order.begin()+d, order.begin()+pos, order.begin()+pos+1);
                ++moves;
            }
            uint64_t covered = 0, black = 0, target = 0;
            for (int k: order) { black |= plates[k].black & ~covered; covered |= plates[k].opaque; }
            const auto& a = in.a[in.requests[r]];
            for (int j = 0; j < in.n; ++j) if (a[j] == '1') target |= uint64_t(1) << j;
            mistakes += black != target;
        }
        std::fclose(child_in); child_in = nullptr;
        std::string extra;
        while (reader.next(extra)) error = "Extra output after the last turn";
    } catch (const std::exception& e) { error = e.what(); }
    if (child_in) {
        if (!error.empty()) { std::fprintf(child_in, "-1\n"); std::fflush(child_in); }
        std::fclose(child_in);
    }
    std::fflush(stdout);
    int status = 0;
    pid_t done = waitpid(pid, &status, WNOHANG);
    if (done == 0 && error.empty()) done = waitpid(pid, &status, 0);
    if (done == 0) { kill(pid, SIGKILL); waitpid(pid, &status, 0); }
    else if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) error = "Your program terminated abnormally";
    std::fclose(child_out);
    if (error.empty()) std::fprintf(stderr, "Score = %lld\n", 2LL*in.k*mistakes + moves);
    else std::fprintf(stderr, "%s\nScore = 0\n", error.c_str());
    return 0;
}
