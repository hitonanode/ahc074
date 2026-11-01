// Local C++ port of tools/src/lib.rs for environments without a Rust toolchain.
// This is an evaluator, not a submitted solver. Each request is sent only after
// the preceding request's entire response has been checked.
#include <algorithm>
#include <cerrno>
#include <charconv>
#include <cctype>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

using u64 = std::uint64_t;

struct Tokens {
    FILE* stream;
    std::vector<std::string> pending;
    size_t pos = 0;
    char* buffer = nullptr;
    size_t capacity = 0;
    size_t relayed_bytes = 0;
    u64 relayed_fnv = 14695981039346656037ULL;
    ~Tokens() { std::free(buffer); }
    bool next(std::string& out) {
        while (pos == pending.size()) {
            const ssize_t size = getline(&buffer, &capacity, stream);
            if (size < 0) return false;
            const size_t written = std::fwrite(buffer, 1, size, stdout);
            if (written != size_t(size))
                throw std::runtime_error("Output relay write failed: " + std::string(std::strerror(errno)));
            relayed_bytes += written;
            for (size_t j = 0; j < written; ++j) {
                relayed_fnv ^= static_cast<unsigned char>(buffer[j]);
                relayed_fnv *= 1099511628211ULL;
            }
            pending.clear();
            pos = 0;
            size_t p = 0;
            while (p < size_t(size)) {
                while (p < size_t(size) && std::isspace(static_cast<unsigned char>(buffer[p]))) ++p;
                const size_t start = p;
                while (p < size_t(size) && !std::isspace(static_cast<unsigned char>(buffer[p]))) ++p;
                if (p > start) pending.emplace_back(buffer + start, p - start);
            }
        }
        out = pending[pos++];
        return true;
    }
    std::string take() {
        std::string out;
        if (!next(out)) throw std::runtime_error("Unexpected EOF");
        return out;
    }
    size_t number(size_t limit) {
        const std::string token = take();
        const char* begin = token.data();
        const char* end = begin + token.size();
        if (begin != end && *begin == '+') ++begin;
        size_t value = 0;
        const auto parsed = std::from_chars(begin, end, value);
        if (begin == end || parsed.ec != std::errc{} || parsed.ptr != end)
            throw std::runtime_error("Parse error: " + token.substr(0, 40));
        if (value >= limit) throw std::runtime_error("Out of range: " + std::to_string(value));
        return value;
    }
};

int main(int argc, char** argv) {
    if (argc < 2) { std::cerr << "Usage: tester <solver> [args...]\n"; return 1; }
    const auto started = std::chrono::steady_clock::now();
    std::signal(SIGPIPE, SIG_IGN);
    int n, k, p, r;
    if (!(std::cin >> n >> k >> p >> r) || n < 1 || n > 64 || k <= 0 || p <= 0 || r < 0) return 1;
    std::vector<std::string> barcode(p);
    std::vector<u64> target(p);
    for (int i = 0; i < p; ++i) {
        std::cin >> barcode[i];
        for (int j = 0; j < n; ++j) if (barcode[i][j] == '1') target[i] |= u64(1) << j;
    }
    std::vector<int> requests(r);
    for (int& x : requests) std::cin >> x;
    int child_in[2], child_out[2];
    if (pipe(child_in) || pipe(child_out)) { std::perror("pipe"); return 1; }
    const pid_t child = fork();
    if (child < 0) { std::perror("fork"); return 1; }
    if (child == 0) {
        dup2(child_in[0], STDIN_FILENO);
        dup2(child_out[1], STDOUT_FILENO);
        close(child_in[0]); close(child_in[1]); close(child_out[0]); close(child_out[1]);
        execvp(argv[1], argv + 1);
        std::perror("failed to execute the command");
        _exit(127);
    }
    close(child_in[0]); close(child_out[1]);
    FILE* send = fdopen(child_in[1], "w");
    FILE* receive = fdopen(child_out[0], "r");
    Tokens tokens{receive};
    std::fprintf(send, "%d %d %d %d\n", n, k, p, r);
    for (const auto& s : barcode) std::fprintf(send, "%s\n", s.c_str());
    std::fflush(send);
    std::vector<u64> opaque(k), black(k);
    std::vector<int> order(k);
    std::iota(order.begin(), order.end(), 0);
    long long moves = 0, mistakes = 0;
    std::string error;
    try {
        for (int i = 0; i < k; ++i) {
            const auto s = tokens.take();
            if (s.size() != size_t(n) || s.find_first_not_of("01.") != std::string::npos)
                throw std::runtime_error("Expected a paper pattern of length N using 0, 1, .");
            for (int j = 0; j < n; ++j) {
                if (s[j] != '.') opaque[i] |= u64(1) << j;
                if (s[j] == '1') black[i] |= u64(1) << j;
            }
        }
        for (int t = 0; t < r; ++t) {
            std::fprintf(send, "%d\n", requests[t]);
            std::fflush(send);
            const size_t count = tokens.number(2 * k + 1);
            for (size_t j = 0; j < count; ++j) {
                const size_t paper = tokens.number(k);
                const size_t destination = tokens.number(k);
                u64 exposed = opaque[paper];
                int pos = 0;
                while (exposed && order[pos] != int(paper)) {
                    exposed &= ~opaque[order[pos]];
                    ++pos;
                }
                if (!exposed) throw std::runtime_error("Paper " + std::to_string(paper) + " is not visible");
                order.erase(order.begin() + pos);
                order.insert(order.begin() + destination, paper);
                ++moves;
            }
            u64 covered = 0, shown = 0;
            for (int id : order) {
                shown |= black[id] & ~covered;
                covered |= opaque[id];
            }
            mistakes += shown != target[requests[t]];
        }
    } catch (const std::exception& e) {
        error = e.what();
        std::fprintf(send, "-1\n");
        std::fflush(send);
    }
    std::fclose(send);
    if (error.empty()) {
        try {
            std::string extra;
            while (tokens.next(extra)) error = "Extra output after the last turn";
        } catch (const std::exception& e) {
            error = e.what();
        }
    }
    if (std::fflush(stdout) != 0 || std::ferror(stdout))
        error = "Output relay flush failed: " + std::string(std::strerror(errno));
    int status = 0;
    pid_t result = waitpid(child, &status, WNOHANG);
    if (error.empty()) {
        if (result == 0) result = waitpid(child, &status, 0);
    } else {
        // On malformed output the solver may still wait for input. Allow a
        // normal response to -1, then stop it, as the official tester does.
        for (int i = 0; i < 10 && result == 0; ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
            result = waitpid(child, &status, WNOHANG);
        }
    }
    const bool abnormal = result == child && (!WIFEXITED(status) || WEXITSTATUS(status) != 0);
    if (result == 0) { kill(child, SIGKILL); waitpid(child, &status, 0); }
    std::fclose(receive);
    // These measurements belong to the evaluator and are raw seconds. They do
    // not alter the submitted solver's CLOCK_SCALE or any stopping condition.
    rusage own{}, solver_usage{};
    getrusage(RUSAGE_SELF, &own);
    getrusage(RUSAGE_CHILDREN, &solver_usage);
    auto seconds = [](const timeval& t) { return double(t.tv_sec) + 1e-6 * t.tv_usec; };
    std::cerr << "tester_cpu_sec = " << seconds(own.ru_utime) + seconds(own.ru_stime)
              << "\nsolver_cpu_sec = " << seconds(solver_usage.ru_utime) + seconds(solver_usage.ru_stime)
              << "\ntester_wall_sec = " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count()
              << "\ntester_relay_bytes = " << tokens.relayed_bytes
              << "\ntester_relay_fnv64 = " << std::hex << tokens.relayed_fnv << std::dec
              << '\n';
    if (abnormal) {
        std::cerr << "Your program terminated abnormally\nScore = 0\n";
        return 1;
    }
    if (!error.empty()) std::cerr << error << "\nScore = 0\n";
    else std::cerr << "Score = " << 2LL * k * mistakes + moves << '\n';
    return 0;
}
