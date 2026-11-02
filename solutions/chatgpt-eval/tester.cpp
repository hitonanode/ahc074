// Local C++ port of the interactive/scoring portion of tools/src/lib.rs.
// This is a transparent adapter for environments without Rust, not the official binary.
#include <algorithm>
#include <cerrno>
#include <charconv>
#include <chrono>
#include <cctype>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#ifdef __linux__
#include <sys/prctl.h>
#endif
#include <unistd.h>

namespace {
pid_t child_pid = -1;
void interrupted(int signum) {
    if (child_pid > 0) kill(child_pid, SIGKILL);
    _exit(128 + signum);
}
struct Reader {
    FILE *fp;
    std::deque<std::string> pending;
    char *line = nullptr;
    size_t capacity = 0;
    explicit Reader(FILE *file) : fp(file) {}
    ~Reader() { free(line); }
    // Rust str::split_whitespace accepts Unicode White_Space. Validate UTF-8
    // before tokenization so malformed bytes cannot be silently accepted.
    static bool whitespace(uint32_t cp) {
        return (cp >= 9 && cp <= 13) || cp == 32 || cp == 0x85 || cp == 0xa0 ||
               cp == 0x1680 || (cp >= 0x2000 && cp <= 0x200a) ||
               cp == 0x2028 || cp == 0x2029 || cp == 0x202f || cp == 0x205f || cp == 0x3000;
    }
    static uint32_t decode(const char *s, size_t n, size_t &i) {
        unsigned char a = s[i++];
        if (a < 0x80) return a;
        int more = a >= 0xc2 && a <= 0xdf ? 1 : a >= 0xe0 && a <= 0xef ? 2 :
                   a >= 0xf0 && a <= 0xf4 ? 3 : -1;
        if (more < 0 || i + size_t(more) > n) throw std::runtime_error("not utf-8");
        uint32_t cp = a & ((1u << (6 - more)) - 1);
        for (int t = 0; t < more; ++t) {
            unsigned char b = s[i++];
            if ((b & 0xc0) != 0x80) throw std::runtime_error("not utf-8");
            cp = (cp << 6) | (b & 0x3f);
        }
        if ((more == 1 && cp < 0x80) || (more == 2 && cp < 0x800) ||
            (more == 3 && cp < 0x10000) || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff))
            throw std::runtime_error("not utf-8");
        return cp;
    }
    bool token(std::string &result) {
        while (pending.empty()) {
            ssize_t n = getline(&line, &capacity, fp);
            if (n < 0) return false;
            if (fwrite(line, 1, size_t(n), stdout) != size_t(n))
                throw std::runtime_error("Failed to save solver stdout: " + std::string(std::strerror(errno)));
            size_t i = 0, begin = 0;
            bool in_token = false;
            while (i < size_t(n)) {
                size_t at = i;
                uint32_t cp = decode(line, size_t(n), i);
                if (whitespace(cp)) {
                    if (in_token) pending.emplace_back(line + begin, at - begin);
                    in_token = false;
                } else if (!in_token) { begin = at; in_token = true; }
            }
            if (in_token) pending.emplace_back(line + begin, size_t(n) - begin);
        }
        result = std::move(pending.front());
        pending.pop_front();
        return true;
    }
    std::string required() {
        std::string s;
        if (!token(s)) throw std::runtime_error("Unexpected EOF");
        return s;
    }
    int integer(int lo, int hi) {
        std::string s = required();
        auto begin = s.data(), end = begin + s.size();
        if (begin != end && *begin == '+') ++begin;
        unsigned long long x = 0;
        auto [last, ec] = std::from_chars(begin, end, x);
        if (ec != std::errc() || last != end || begin == end)
            throw std::runtime_error("Parse error: " + s.substr(0, 40));
        if (x < static_cast<unsigned long long>(lo) || x > static_cast<unsigned long long>(hi))
            throw std::runtime_error("Out of range: " + s.substr(0, 40));
        return int(x);
    }
};
uint64_t mask(const std::string &s, char ch) {
    uint64_t r = 0;
    for (size_t j = 0; j < s.size(); ++j) if (s[j] == ch) r |= uint64_t(1) << j;
    return r;
}
// stdout/stderr are regular files in the paired runner, but pipes in selftests.
// Check every write and explicitly persist files before reporting completion.
bool sync_regular_file(int fd) {
    struct stat status;
    if (fstat(fd, &status) != 0) return false;
    if (!S_ISREG(status.st_mode)) return true;
    int result;
    do { result = fsync(fd); } while (result < 0 && errno == EINTR);
    return result == 0;
}
} // namespace

int main(int argc, char **argv) {
    if (argc < 2) { std::cerr << "Usage: tester <command> [args...]\n"; return 1; }
    int N, K, P, R;
    if (!(std::cin >> N >> K >> P >> R) || N < 1 || N > 64 || K < 1 || P < 1 || R < 1) {
        std::cerr << "Invalid test input\nScore = 0\n"; return 1;
    }
    std::vector<std::string> A(P);
    std::vector<int> requests(R);
    for (auto &s : A) {
        if (!(std::cin >> s) || s.size() != size_t(N) || s.find_first_not_of("01") != std::string::npos) {
            std::cerr << "Invalid test input\nScore = 0\n"; return 1;
        }
    }
    for (auto &r : requests) {
        if (!(std::cin >> r) || r < 0 || r >= P) {
            std::cerr << "Invalid test input\nScore = 0\n"; return 1;
        }
    }
    int to_child[2], from_child[2];
    if (pipe(to_child) || pipe(from_child)) { perror("pipe"); return 1; }
    std::signal(SIGPIPE, SIG_IGN);
    std::signal(SIGTERM, interrupted);
    std::signal(SIGINT, interrupted);
    const pid_t tester_pid = getpid();
    child_pid = fork();
    if (child_pid < 0) { perror("fork"); return 1; }
    if (child_pid == 0) {
#ifdef __linux__
        // The paired runner may SIGKILL this tester on timeout. Kill the solver
        // automatically too, including the race where the parent dies first.
        prctl(PR_SET_PDEATHSIG, SIGKILL);
        if (getppid() != tester_pid) _exit(1);
#else
        (void)tester_pid;
#endif
        dup2(to_child[0], STDIN_FILENO);
        dup2(from_child[1], STDOUT_FILENO);
        close(to_child[0]); close(to_child[1]); close(from_child[0]); close(from_child[1]);
        execvp(argv[1], argv + 1);
        perror("execvp"); _exit(127);
    }
    close(to_child[0]); close(from_child[1]);
    FILE *input = fdopen(to_child[1], "w");
    FILE *output = fdopen(from_child[0], "r");
    setvbuf(stdout, nullptr, _IOFBF, 65536);
    Reader reader{output};
    std::vector<uint64_t> opaque(K), black(K);
    std::vector<int> order(K);
    std::iota(order.begin(), order.end(), 0);
    long long moves = 0, mistakes = 0;
    std::string error;
    fprintf(input, "%d %d %d %d\n", N, K, P, R);
    for (const auto &s : A) fprintf(input, "%s\n", s.c_str());
    fflush(input);
    try {
        for (int k = 0; k < K; ++k) {
            auto s = reader.required();
            if (s.size() != size_t(N) || s.find_first_not_of("01.") != std::string::npos)
                throw std::runtime_error("Expected a paper pattern of length N using 0, 1, .");
            black[k] = mask(s, '1');
            opaque[k] = black[k] | mask(s, '0');
        }
        for (int r = 0; r < R; ++r) {
            fprintf(input, "%d\n", requests[r]); fflush(input);
            const int count = reader.integer(0, 2 * K);
            for (int m = 0; m < count; ++m) {
                int k = reader.integer(0, K - 1), d = reader.integer(0, K - 1);
                uint64_t exposed = opaque[k];
                int pos = 0;
                while (exposed && order[pos] != k) {
                    exposed &= ~opaque[order[pos]];
                    ++pos;
                }
                if (!exposed) throw std::runtime_error("Paper " + std::to_string(k) + " is not visible");
                if (pos < d) std::rotate(order.begin() + pos, order.begin() + pos + 1, order.begin() + d + 1);
                else std::rotate(order.begin() + d, order.begin() + pos, order.begin() + pos + 1);
                ++moves;
            }
            uint64_t covered = 0, shown = 0;
            for (int k : order) {
                shown |= black[k] & ~covered;
                covered |= opaque[k];
            }
            if (shown != mask(A[requests[r]], '1')) ++mistakes;
        }
        fclose(input); input = nullptr;
        std::string extra;
        while (reader.token(extra)) error = "Extra output after the last turn";
    } catch (const std::exception &e) {
        error = e.what();
        if (input) { fputs("-1\n", input); fflush(input); }
    }
    if (input) fclose(input);
    fclose(output);
    if (fflush(stdout) != 0 || !sync_regular_file(STDOUT_FILENO))
        error = "Failed to persist solver stdout: " + std::string(std::strerror(errno));
    int status = 0;
    pid_t ended = 0;
    for (int i = 0; i < 10 && ended == 0; ++i) {
        ended = waitpid(child_pid, &status, WNOHANG);
        if (!ended) std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    bool abnormal = ended == child_pid && (!WIFEXITED(status) || WEXITSTATUS(status) != 0);
    if (!ended) { kill(child_pid, SIGKILL); waitpid(child_pid, &status, 0); }
    child_pid = -1;
    if (abnormal) error = "Your program terminated abnormally";
    if (error.empty()) std::cerr << "Score = " << 2LL * K * mistakes + moves << '\n';
    else std::cerr << error << "\nScore = 0\n";
    std::cerr.flush();
    if (!std::cerr || fflush(stderr) != 0 || !sync_regular_file(STDERR_FILENO)) {
        std::cerr.clear();
        std::cerr << "Failed to persist tester stderr\nScore = 0\n" << std::flush;
        fflush(stderr);
        sync_regular_file(STDERR_FILENO);
        return 2;
    }
    return abnormal ? 1 : 0;
}
