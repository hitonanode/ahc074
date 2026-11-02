// Portable local tester, a direct translation of tools/src/lib.rs interaction rules.
// This is research tooling, not the submitted solver. POSIX process APIs are intentional.
#include <algorithm>
#include <cerrno>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

using u64 = std::uint64_t;

int main(int argc, char** argv) {
    if (argc < 2) return 1;
    int n, k, p, r;
    if (!(std::cin >> n >> k >> p >> r)) return 1;
    std::vector<std::string> targets(p);
    std::vector<int> requests(r);
    for (auto& s : targets) std::cin >> s;
    for (auto& q : requests) std::cin >> q;
    int to_child[2], from_child[2], errors_child[2];
    if (pipe(to_child) || pipe(from_child) || pipe(errors_child)) return 1;
    const pid_t child = fork();
    if (child < 0) return 1;
    if (!child) {
        dup2(to_child[0], STDIN_FILENO);
        dup2(from_child[1], STDOUT_FILENO);
        dup2(errors_child[1], STDERR_FILENO);
        close(to_child[0]); close(to_child[1]);
        close(from_child[0]); close(from_child[1]);
        close(errors_child[0]); close(errors_child[1]);
        execvp(argv[1], argv + 1);
        _exit(127);
    }
    close(to_child[0]); close(from_child[1]); close(errors_child[1]);
    signal(SIGPIPE, SIG_IGN);
    FILE* writer = fdopen(to_child[1], "w");
    FILE* reader = fdopen(from_child[0], "r");
    std::string solver_errors, relay;
    std::thread error_reader([&] {
        char buffer[4096];
        for (;;) {
            const ssize_t nread = read(errors_child[0], buffer, sizeof(buffer));
            if (nread > 0) solver_errors.append(buffer, std::size_t(nread));
            else if (nread < 0 && errno == EINTR) continue;
            else break;
        }
        close(errors_child[0]);
    });
    setvbuf(stdout, nullptr, _IOFBF, 65536);
    auto token = [&]() {
        std::string s;
        for (;;) {
            const int ch = fgetc(reader);
            if (ch == EOF) return s;
            relay.push_back(char(ch));
            if (ch == ' ' || ch == '\n' || ch == '\r' || ch == '\t' || ch == '\f' || ch == '\v') {
                if (!s.empty()) return s;
            } else s.push_back(char(ch));
            if (s.size() > 100000) throw std::runtime_error("Token too long");
        }
    };
    auto number = [&](int limit) {
        const std::string s = token();
        if (s.empty()) throw std::runtime_error("Unexpected EOF");
        std::size_t at = s[0] == '+' ? 1 : 0;
        if (at == s.size()) throw std::runtime_error("Parse error");
        unsigned long long v = 0;
        for (; at < s.size(); ++at) {
            if (s[at] < '0' || s[at] > '9') throw std::runtime_error("Parse error");
            v = v * 10 + unsigned(s[at] - '0');
            if (v >= unsigned(limit)) throw std::runtime_error("Out of range");
        }
        return int(v);
    };
    auto mask = [](const std::string& s, char c) {
        u64 v = 0;
        for (unsigned j = 0; j < s.size(); ++j) if (s[j] == c) v |= u64(1) << j;
        return v;
    };
    std::vector<u64> opaque(k), black(k);
    std::vector<int> order(k);
    std::iota(order.begin(), order.end(), 0);
    long long moves = 0, mistakes = 0;
    std::string error;
    fprintf(writer, "%d %d %d %d\n", n, k, p, r);
    for (const auto& s : targets) fprintf(writer, "%s\n", s.c_str());
    fflush(writer);
    try {
        for (int i = 0; i < k; ++i) {
            const auto s = token();
            if (int(s.size()) != n || s.find_first_not_of("01.") != std::string::npos)
                throw std::runtime_error("Expected a paper pattern of length N using 0, 1, .");
            opaque[i] = mask(s, '0') | mask(s, '1');
            black[i] = mask(s, '1');
        }
        for (int t = 0; t < r; ++t) {
            fprintf(writer, "%d\n", requests[t]); fflush(writer);
            const int count = number(2 * k + 1);
            for (int z = 0; z < count; ++z) {
                const int id = number(k), d = number(k);
                u64 exposed = opaque[id];
                int pos = 0;
                while (exposed && order[pos] != id) exposed &= ~opaque[order[pos++]];
                if (!exposed) throw std::runtime_error("Paper " + std::to_string(id) + " is not visible");
                if (pos < d) std::rotate(order.begin()+pos, order.begin()+pos+1, order.begin()+d+1);
                else std::rotate(order.begin()+d, order.begin()+pos, order.begin()+pos+1);
                ++moves;
            }
            u64 covered = 0, shown = 0;
            for (int id : order) {
                shown |= black[id] & ~covered;
                covered |= opaque[id];
            }
            mistakes += shown != mask(targets[requests[t]], '1');
        }
        fclose(writer); writer = nullptr;
        if (!token().empty()) throw std::runtime_error("Extra output after the last turn");
    } catch (const std::exception& e) {
        error = e.what();
        if (writer) { fprintf(writer, "-1\n"); fflush(writer); }
    }
    if (writer) fclose(writer);
    int status = 0;
    if (error.empty()) waitpid(child, &status, 0);
    else { kill(child, SIGKILL); waitpid(child, &status, 0); }
    fclose(reader);
    error_reader.join();
    fwrite(relay.data(), 1, relay.size(), stdout);
    fflush(stdout);
    if (error.empty() && (!WIFEXITED(status) || WEXITSTATUS(status))) error = "Your program terminated abnormally";
    if (!error.empty()) solver_errors += error + "\nScore = 0\n";
    else solver_errors += "Score = " + std::to_string(2LL * k * mistakes + moves) + "\n";
    fwrite(solver_errors.data(), 1, solver_errors.size(), stderr);
    fflush(stderr);
    // Ensure relay and metrics are durably written before the evaluation wrapper records success.
    // This does not alter the interaction or score; it protects reproducible output archives.
    std::cerr.flush();
    fsync(STDOUT_FILENO);
    fsync(STDERR_FILENO);
    return 0;
}
