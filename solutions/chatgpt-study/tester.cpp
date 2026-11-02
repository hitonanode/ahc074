// ASCII-protocol port of tools/src/lib.rs and tools/src/bin/tester.rs.
// Kept separate from the official source; see README.md for provenance.
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

struct Plate { uint64_t opaque = 0, black = 0; };

// Read complete lines, relay the original bytes, then split into tokens just as
// the official tester does. No future request is written until this turn ends.
class Tokens {
    FILE *file;
    char *line = nullptr;
    size_t capacity = 0;
    std::string current;
    size_t pos = 0;
public:
    explicit Tokens(FILE *f) : file(f) {}
    ~Tokens() { std::free(line); }
    bool next(std::string &token) {
        for (;;) {
            while (pos < current.size() && std::isspace(static_cast<unsigned char>(current[pos]))) ++pos;
            if (pos < current.size()) {
                size_t start = pos;
                while (pos < current.size() && !std::isspace(static_cast<unsigned char>(current[pos]))) ++pos;
                token = current.substr(start, pos - start);
                return true;
            }
            ssize_t length = ::getline(&line, &capacity, file);
            if (length < 0) return false;
            if (std::fwrite(line, 1, static_cast<size_t>(length), stdout) != static_cast<size_t>(length))
                throw std::runtime_error("Cannot relay output");
            current.assign(line, static_cast<size_t>(length));
            pos = 0;
        }
    }
    std::string required() {
        std::string value;
        if (!next(value)) throw std::runtime_error("Unexpected EOF");
        return value;
    }
    int integer(int lo, int hi) {
        std::string text = required();
        std::string_view view(text);
        if (view.starts_with('+')) view.remove_prefix(1);
        unsigned long long value = 0;
        auto [end, ec] = std::from_chars(view.data(), view.data() + view.size(), value);
        if (view.empty() || ec != std::errc{} || end != view.data() + view.size())
            throw std::runtime_error("Parse error: " + text.substr(0, 40));
        if (value < static_cast<unsigned long long>(lo) || value > static_cast<unsigned long long>(hi))
            throw std::runtime_error("Out of range: " + text.substr(0, 40));
        return static_cast<int>(value);
    }
};

int main(int argc, char **argv) {
    if (argc < 2) { std::cerr << "Usage: tester <command> [args...]\n"; return 1; }
    int n, k, p, r;
    if (!(std::cin >> n >> k >> p >> r) || n < 1 || n > 64 || k < 1 || p < 1 || r < 1)
        return 1;
    std::vector<std::string> patterns(p);
    std::vector<uint64_t> target(p);
    std::vector<int> requests(r);
    for (int i = 0; i < p; ++i) {
        std::cin >> patterns[i];
        if (static_cast<int>(patterns[i].size()) != n) return 1;
        for (int j = 0; j < n; ++j) if (patterns[i][j] == '1') target[i] |= uint64_t{1} << j;
    }
    for (int &request : requests) {
        if (!(std::cin >> request) || request < 0 || request >= p) return 1;
    }
    int to_child[2], from_child[2];
    if (::pipe(to_child) || ::pipe(from_child)) return 1;
    std::signal(SIGPIPE, SIG_IGN);
    pid_t child = ::fork();
    if (child < 0) return 1;
    if (child == 0) {
        std::signal(SIGPIPE, SIG_DFL);
        ::dup2(to_child[0], STDIN_FILENO);
        ::dup2(from_child[1], STDOUT_FILENO);
        ::close(to_child[0]); ::close(to_child[1]);
        ::close(from_child[0]); ::close(from_child[1]);
        ::execvp(argv[1], argv + 1);
        std::perror("execvp");
        ::_exit(127);
    }
    ::close(to_child[0]); ::close(from_child[1]);
    FILE *send = ::fdopen(to_child[1], "w");
    FILE *receive = ::fdopen(from_child[0], "r");
    std::setvbuf(stdout, nullptr, _IOFBF, 65536);
    std::fprintf(send, "%d %d %d %d\n", n, k, p, r);
    for (const auto &s : patterns) std::fprintf(send, "%s\n", s.c_str());
    std::fflush(send);
    int mistakes = 0, moves = 0;
    std::string error;
    try {
        Tokens tokens(receive);
        std::vector<Plate> plates(k);
        for (auto &plate : plates) {
            std::string s = tokens.required();
            if (static_cast<int>(s.size()) != n || s.find_first_not_of("01.") != std::string::npos)
                throw std::runtime_error("Expected a paper pattern of length N using 0, 1, .");
            for (int j = 0; j < n; ++j) {
                if (s[j] != '.') plate.opaque |= uint64_t{1} << j;
                if (s[j] == '1') plate.black |= uint64_t{1} << j;
            }
        }
        std::vector<int> order(k);
        std::iota(order.begin(), order.end(), 0);
        for (int query = 0; query < r; ++query) {
            std::fprintf(send, "%d\n", requests[query]);
            std::fflush(send);
            int count = tokens.integer(0, 2 * k);
            for (int j = 0; j < count; ++j) {
                int id = tokens.integer(0, k - 1), depth = tokens.integer(0, k - 1);
                uint64_t exposed = plates[id].opaque;
                int pos = 0;
                while (exposed && order[pos] != id) {
                    exposed &= ~plates[order[pos]].opaque;
                    ++pos;
                }
                if (!exposed) throw std::runtime_error("Paper " + std::to_string(id) + " is not visible");
                if (pos < depth) std::rotate(order.begin() + pos, order.begin() + pos + 1, order.begin() + depth + 1);
                else std::rotate(order.begin() + depth, order.begin() + pos, order.begin() + pos + 1);
                ++moves;
            }
            uint64_t black = 0, covered = 0;
            for (int id : order) {
                black |= plates[id].black & ~covered;
                covered |= plates[id].opaque;
            }
            mistakes += black != target[requests[query]];
        }
        // EOF is necessary: otherwise an extra operation after the last query
        // could silently pass. Closing stdin lets a well-behaved solver exit.
        std::fclose(send);
        send = nullptr;
        std::string extra;
        while (tokens.next(extra)) error = "Extra output after the last turn";
    } catch (const std::exception &e) {
        error = e.what();
    }
    if (send) {
        std::fprintf(send, "-1\n"); std::fflush(send); std::fclose(send);
        ::kill(child, SIGKILL);
    }
    std::fclose(receive);
    std::fflush(stdout);
    // Match the official EOF cleanup: allow the child's exit status to settle
    // for about 10 ms, then kill a process that closed stdout but kept running.
    // The cleanup kill is not itself a solver runtime error.
    int status = 0;
    pid_t waited = 0;
    for (int attempt = 0; attempt < 11; ++attempt) {
        waited = ::waitpid(child, &status, WNOHANG);
        if (waited == child || (waited < 0 && errno != EINTR)) break;
        if (attempt < 10) ::usleep(1000);
    }
    const bool exited_naturally = waited == child;
    if (waited == 0) {
        ::kill(child, SIGKILL);
        while (::waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    }
    if (error.empty() && exited_naturally && (!WIFEXITED(status) || WEXITSTATUS(status) != 0))
        error = "Your program terminated abnormally";
    if (error.empty()) std::cerr << "Score = " << (2LL * k * mistakes + moves) << '\n';
    else std::cerr << error << "\nScore = 0\n";
    return error.empty() ? 0 : 1;
}
