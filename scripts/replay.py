"""Replays AHC074 outputs with the same rules as tools/src/lib.rs, and computes per-case metrics.

scripts/observe.py and scripts/report.py are built on this module. Your own analysis scripts can
import it too:

    import sys
    sys.path.insert(0, "<checkout>/scripts")
    import replay

    inp = replay.load_input(19)
    out = replay.parse_output(inp, (replay.resolve_run("sample") / "out" / "0019.txt").read_text())
    game = replay.Game(inp, out.designs)
    for r, ops in enumerate(out.queries):
        for k, d in ops:
            game.move(k, d)            # raises replay.InvalidMove if paper k is not visible
        correct = game.finish(r)       # True if the display matches the requested barcode
    print(game.score())

Conventions (the same as the tester):
- A barcode or a paper is an int bit mask: bit j is window j (the j-th character of the string).
  A paper has `opaque` (not a hole) and `black` (a '1') masks.
- `Game.order` lists paper ids from top to bottom. move(k, d) takes paper k out and inserts it
  below the top d of the remaining papers (d = 0: top, d = K - 1: bottom).
- The solution's stdout is runs/<run-id>/out/<seed>.txt. Its stderr, followed by the tester's
  verdict lines (an error message, then "Score = ..."), is runs/<run-id>/err/<seed>.txt.
- A solution may print its structure to stderr (the roles of the papers and the purpose of every
  move: `@paper` / `@ops` lines, AGENTS.md). parse_annotations reads them:

    ann = replay.parse_annotations(err_text, inp.k)
    ann.papers["role"][k]          # attribute of paper k (output numbering), '-' for none
    ann.labels_of(r, len(out.queries[r]))   # one label per move of request r
"""

from __future__ import annotations

import functools
import json
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Bump when the contents of metrics.json change, so that stale caches are recomputed.
METRICS_VERSION = 1

_STAT_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.:/-]*)\s*=\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$")


# ---------------------------------------------------------------- locations


@functools.cache
def main_root() -> Path:
    """The main checkout, which holds runs/ and pahcer/ even when called from a worktree."""
    here = Path(__file__).resolve().parent
    common = subprocess.run(
        ["git", "-C", str(here), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return Path(common).parent


def runs_dir() -> Path:
    return main_root() / "runs"


@functools.cache
def config() -> dict:
    """pahcer_config.toml of the main checkout."""
    return tomllib.loads((main_root() / "pahcer_config.toml").read_text())


def all_seeds() -> range:
    """The seeds evaluated by default: [start_seed, end_seed) of pahcer_config.toml."""
    test = config()["test"]
    return range(test["start_seed"], test["end_seed"])


def finished_run_dirs() -> list[Path]:
    """Run directories that finished normally, oldest first."""
    found = []
    if not runs_dir().is_dir():
        return found
    for d in sorted(runs_dir().iterdir()):
        if not d.is_dir() or d.name.startswith(".") or not (d / "result.json").exists():
            continue
        try:
            if json.loads((d / "meta.json").read_text()).get("status") == "ok":
                found.append(d)
        except (OSError, ValueError):
            continue
    return found


def resolve_run(arg: str) -> Path:
    """Finds a run directory from a path, a full run-id, or the solution name at its end.

    If several runs match, the latest one is returned.
    """
    path = Path(arg)
    if path.is_dir() and (path / "meta.json").exists():
        return path.resolve()
    if not runs_dir().is_dir():
        raise LookupError("runs/ がありません")
    names = sorted(d.name for d in runs_dir().iterdir() if d.is_dir() and not d.name.startswith("."))
    for match in (lambda s: s == arg, lambda s: s.endswith("_" + arg), lambda s: arg in s):
        found = [s for s in names if match(s)]
        if found:
            return runs_dir() / found[-1]
    raise LookupError(f"run が見つかりません: {arg}")


def run_scores(run_dir: Path) -> dict[int, int]:
    """Judge scores per seed from the run's result.json (0 means WA)."""
    result = json.loads((run_dir / "result.json").read_text())
    return {case["seed"]: case["score"] for case in result["cases"]}


def run_cases(run_dir: Path) -> dict[int, dict]:
    """The case records of result.json (seed, score, relative_score, execution_time, error_message)."""
    result = json.loads((run_dir / "result.json").read_text())
    return {case["seed"]: case for case in result["cases"]}


def best_scores() -> dict[int, int]:
    """Best score per seed over all recorded evaluations (pahcer/best_scores.json)."""
    path = main_root() / "pahcer" / "best_scores.json"
    if not path.exists():
        return {}
    return {int(seed): score for seed, score in json.loads(path.read_text()).items() if score > 0}


def write_json_atomic(path: Path, data, indent: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n")
    os.replace(tmp, path)


def out_path(run_dir: Path, seed: int) -> Path:
    return run_dir / "out" / f"{seed:04d}.txt"


def err_path(run_dir: Path, seed: int) -> Path:
    return run_dir / "err" / f"{seed:04d}.txt"


# ---------------------------------------------------------------- input and output


def mask(s: str, c: str) -> int:
    """Bit mask of the positions of character c in s (bit j = s[j])."""
    m = 0
    for j, ch in enumerate(s):
        if ch == c:
            m |= 1 << j
    return m


def mask_text(m: int, n: int) -> str:
    """A barcode mask as a 0/1 string (window 0 first)."""
    return "".join("1" if m >> j & 1 else "0" for j in range(n))


@dataclass
class Input:
    n: int
    k: int
    p: int
    r: int
    barcodes: list[str]   # A_0 .. A_{P-1}
    requests: list[int]   # a_0 .. a_{R-1}
    target: list[int] = field(init=False)  # A_v as a mask of black windows

    def __post_init__(self):
        self.target = [mask(a, "1") for a in self.barcodes]

    @property
    def full(self) -> int:
        return (1 << self.n) - 1


def parse_input(text: str) -> Input:
    tokens = text.split()
    n, k, p, r = map(int, tokens[:4])
    barcodes = tokens[4:4 + p]
    requests = list(map(int, tokens[4 + p:4 + p + r]))
    return Input(n, k, p, r, barcodes, requests)


@functools.cache
def load_input(seed: int) -> Input:
    return parse_input((main_root() / "tools" / "in" / f"{seed:04d}.txt").read_text())


@dataclass
class Paper:
    pattern: str
    opaque: int
    black: int


@dataclass
class Output:
    designs: list[Paper]
    queries: list[list[tuple[int, int]]]  # one list of (k, d) per processed request
    error: str | None                      # the tester's message if the output is invalid

    @property
    def moves(self) -> int:
        return sum(len(q) for q in self.queries)


def parse_output(inp: Input, text: str) -> Output:
    """Parses the solution's stdout the way the tester reads it (whitespace-separated tokens).

    Format errors stop the parse; the designs and queries read before it are kept, and error is
    set. Visibility of moved papers is not checked here (Game.move does it).
    """
    tokens = text.split()
    pos = 0
    designs: list[Paper] = []
    queries: list[list[tuple[int, int]]] = []

    def take() -> str | None:
        nonlocal pos
        if pos >= len(tokens):
            return None
        pos += 1
        return tokens[pos - 1]

    def number(lo: int, hi: int) -> int:  # [lo, hi]
        t = take()
        if t is None:
            raise ValueError("Unexpected EOF")
        try:
            v = int(t)
        except ValueError:
            raise ValueError(f"Parse error: {t[:40]}") from None
        if not lo <= v <= hi:
            raise ValueError(f"Out of range: {v}")
        return v

    try:
        for _ in range(inp.k):
            s = take()
            if s is None:
                raise ValueError("Unexpected EOF")
            if len(s) != inp.n or any(c not in "01." for c in s):
                raise ValueError("Expected a paper pattern of length N using 0, 1, .")
            designs.append(Paper(s, mask(s, "0") | mask(s, "1"), mask(s, "1")))
        for _ in range(inp.r):
            m = number(0, 2 * inp.k)
            ops = []
            queries.append(ops)
            for _ in range(m):
                k = number(0, inp.k - 1)
                d = number(0, inp.k - 1)
                ops.append((k, d))
        if pos < len(tokens):
            raise ValueError("Extra output after the last turn")
    except ValueError as e:
        return Output(designs, queries, str(e))
    return Output(designs, queries, None)


# ---------------------------------------------------------------- simulation


class InvalidMove(Exception):
    pass


class Game:
    """The stack of papers. order[0] is the top paper."""

    def __init__(self, inp: Input, designs: list[Paper]):
        self.inp = inp
        self.papers = designs
        self.order = list(range(inp.k))
        self.moves = 0
        self.mistakes = 0
        self.completed = 0

    def position(self, k: int) -> int:
        """Index of paper k in order (0 = top)."""
        return self.order.index(k)

    def exposed_of(self, k: int) -> int:
        """Windows where paper k is the visible paper."""
        covered = 0
        for x in self.order:
            if x == k:
                return self.papers[k].opaque & ~covered
            covered |= self.papers[x].opaque
        return 0

    def exposed(self) -> dict[int, int]:
        """Visible windows of every paper that shows at least one window, in stack order."""
        covered = 0
        found = {}
        for x in self.order:
            e = self.papers[x].opaque & ~covered
            if e:
                found[x] = e
            covered |= self.papers[x].opaque
            if covered == self.inp.full:
                break
        return found

    def display(self) -> int:
        """The displayed barcode as a mask of black windows (uncovered windows are white)."""
        covered = 0
        black = 0
        full = self.inp.full
        papers = self.papers
        for x in self.order:
            p = papers[x]
            black |= p.black & ~covered
            covered |= p.opaque
            if covered == full:
                break
        return black

    def move(self, k: int, d: int, check: bool = True) -> int:
        """Applies move (k, d) and returns the position paper k had before it.

        With check, raises InvalidMove if paper k shows no window (as the tester does).
        """
        pos = self.order.index(k)
        if check:
            covered = 0
            for x in self.order[:pos]:
                covered |= self.papers[x].opaque
            if not self.papers[k].opaque & ~covered:
                raise InvalidMove(f"Paper {k} is not visible")
        self.order.pop(pos)
        self.order.insert(d, k)
        self.moves += 1
        return pos

    def finish(self, r: int) -> bool:
        """Ends request r; returns whether the display matches it."""
        ok = self.display() == self.inp.target[self.inp.requests[r]]
        if not ok:
            self.mistakes += 1
        self.completed += 1
        return ok

    def score(self) -> int:
        return 2 * self.inp.k * self.mistakes + self.moves


@dataclass
class QueryRecord:
    r: int
    target: int        # requested barcode id a_r
    ops: list[tuple[int, int]]
    positions: list[int]  # position of each moved paper before its move (0 = top)
    correct: bool
    mismatch: int      # windows that differ from the requested barcode


@dataclass
class Replay:
    inp: Input
    out: Output
    queries: list[QueryRecord]
    error: str | None  # first error (format or invalid move); the judge scores 0 if set
    game: Game

    @property
    def score(self) -> int:
        return 0 if self.error else self.game.score()


def replay(inp: Input, out: Output, check: bool = True, stop_after: int | None = None) -> Replay:
    """Replays the output. stop_after = r stops after request r - 1 (the state before request r)."""
    if len(out.designs) < inp.k:
        return Replay(inp, out, [], out.error or "Unexpected EOF", Game(inp, out.designs))
    game = Game(inp, out.designs)
    records = []
    error = None
    limit = len(out.queries) if stop_after is None else min(stop_after, len(out.queries))
    for r in range(limit):
        ops = out.queries[r]
        positions = []
        try:
            for k, d in ops:
                positions.append(game.move(k, d, check))
        except InvalidMove as e:
            error = f"request {r}, move {len(positions)}: {e}"
            break
        target = inp.requests[r]
        shown = game.display()
        correct = game.finish(r)
        records.append(QueryRecord(r, target, ops, positions, correct, (shown ^ inp.target[target]).bit_count()))
    if error is None and stop_after is None:
        error = out.error
    return Replay(inp, out, records, error, game)


# ---------------------------------------------------------------- metrics


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    return s[min(len(s) - 1, int(q * (len(s) - 1) + 0.5))]


def design_metrics(inp: Input, designs: list[Paper]) -> dict:
    holes = [inp.n - p.opaque.bit_count() for p in designs]
    return {
        "hole_share": sum(holes) / (inp.n * len(designs)) if designs else float("nan"),
        "papers_all_holes": sum(h == inp.n for h in holes),
        "papers_no_holes": sum(h == 0 for h in holes),
    }


def case_metrics(inp: Input, out: Output) -> dict:
    """Behaviour metrics of one case. Replays without the visibility check (the tester did it)."""
    rep = replay(inp, out, check=False)
    q = rep.queries
    counts = [len(x.ops) for x in q]
    positions = [p for x in q for p in x.positions]
    ds = [d for x in q for _, d in x.ops]
    wrong = [x for x in q if not x.correct]
    m = {
        "score": rep.score,
        "E": rep.game.mistakes,
        "T": rep.game.moves,
        "requests": len(q),
        "ops_mean": sum(counts) / len(counts) if counts else float("nan"),
        "ops_p50": percentile(counts, 0.5),
        "ops_p90": percentile(counts, 0.9),
        "ops_max": max(counts, default=0),
        "zero_op_share": sum(c == 0 for c in counts) / len(counts) if counts else float("nan"),
        "mismatch_on_wrong": sum(x.mismatch for x in wrong) / len(wrong) if wrong else 0.0,
        "moved_pos_mean": sum(positions) / len(positions) if positions else float("nan"),
        "insert_d_mean": sum(ds) / len(ds) if ds else float("nan"),
        "to_bottom_share": sum(d == inp.k - 1 for d in ds) / len(ds) if ds else float("nan"),
        "to_top_share": sum(d == 0 for d in ds) / len(ds) if ds else float("nan"),
        "distinct_papers_moved": len({k for x in q for k, _ in x.ops}),
        "error": rep.error or "",
    }
    m.update(design_metrics(inp, out.designs))
    return m


def stderr_stats(text: str) -> dict[str, float]:
    """Values printed to stderr as `name = number` (the last one wins). The tester's `Score = ...`
    line at the end of the err file and the structure lines (`@...`, parse_annotations) are left out."""
    found = {}
    for line in text.splitlines():
        if line.startswith("@"):
            continue
        match = _STAT_LINE.match(line)
        if match and match[1] != "Score":
            found[match[1]] = float(match[2])
    return found


# ---------------------------------------------------------------- annotations (the solution's structure)

# Bump when the contents of annotations.json change.
ANNOTATIONS_VERSION = 1
# Per case, moves are counted by the value of the moved paper's attributes that have at most this many
# distinct values (the others, e.g. the targets of a paper, are only shown per paper), and per label and
# value for the attributes with at most ANNOTATION_CROSS_VALUES values.
ANNOTATION_ATTR_VALUES = 40
ANNOTATION_CROSS_VALUES = 8
_ANNOTATION_LINE = re.compile(r"^@(\w+)\s+(\S+)\s*=(.*)$")


@dataclass
class Annotations:
    """The structure that a solution prints to stderr (AGENTS.md, the analysis section), independent of
    the solution:

        @paper <name> = <value of paper 0> <value of paper 1> ... <value of paper K-1>
        @ops <r> = <label of move 0 of request r> <label of move 1> ...

    Papers are numbered as output; '-' is no value. `label*n` stands for n times the label. Lines of
    other kinds `@<kind> ...` are kept in `other` and not interpreted.
    """
    papers: dict[str, list[str]] = field(default_factory=dict)  # attribute -> value per paper
    ops: dict[int, list[str]] = field(default_factory=dict)     # request -> label per move
    other: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)           # lines that do not fit the format

    def __bool__(self) -> bool:
        return bool(self.papers or self.ops)

    def value(self, name: str, k: int) -> str:
        values = self.papers.get(name)
        return values[k] if values and 0 <= k < len(values) else "-"

    def labels_of(self, r: int, moves: int) -> list[str]:
        """The labels of the moves of request r ('?' where missing or of the wrong number)."""
        labels = self.ops.get(r)
        return labels if labels is not None and len(labels) == moves else ["?"] * moves


def _expand_labels(tokens: list[str]) -> list[str]:
    labels = []
    for t in tokens:
        name, star, count = t.rpartition("*")
        if star and name and count.isdigit():
            labels.extend([name] * int(count))
        else:
            labels.append(t)
    return labels


def parse_annotations(text: str, k: int | None = None) -> Annotations:
    """The `@` lines of a stderr text (the last line of a name or request wins). With k, `@paper` lines
    of another length are problems (and left out)."""
    ann = Annotations()
    for line in text.splitlines():
        if not line.startswith("@"):
            continue
        match = _ANNOTATION_LINE.match(line.rstrip())
        if not match:
            ann.problems.append(f"bad line: {line[:60]}")
            continue
        kind, key, values = match[1], match[2], match[3].split()
        if kind == "paper":
            if k is not None and len(values) != k:
                ann.problems.append(f"@paper {key}: {len(values)} values for {k} papers")
                continue
            ann.papers[key] = values
        elif kind == "ops":
            if not key.isdigit():
                ann.problems.append(f"@ops {key}: not a request number")
                continue
            ann.ops[int(key)] = _expand_labels(values)
        else:
            ann.other.append(line)
    return ann


def check_annotations(ann: Annotations, out: Output) -> list[str]:
    """The problems of the annotations of an output: format problems, and requests whose `@ops` line
    has another number of labels than the request has moves (or is missing while others are there)."""
    problems = list(ann.problems)
    if not ann.ops:
        return problems
    for r, ops in enumerate(out.queries):
        labels = ann.ops.get(r)
        if labels is None:
            if ops:
                problems.append(f"request {r}: no @ops line for {len(ops)} moves")
        elif len(labels) != len(ops):
            problems.append(f"request {r}: {len(labels)} labels for {len(ops)} moves")
    extra = [r for r in ann.ops if r >= len(out.queries)]
    if extra:
        problems.append(f"@ops of {len(extra)} requests not in the output (e.g. {min(extra)})")
    return problems


def annotation_metrics(out: Output, ann: Annotations) -> dict:
    """Per-case counts of the moves by label and by the moved paper's attributes (stats)."""
    problems = check_annotations(ann, out)
    labels: dict[str, int] = {}
    label_requests: dict[str, int] = {}
    attrs = {name: values for name, values in ann.papers.items() if len(set(values)) <= ANNOTATION_ATTR_VALUES}
    cross_attrs = [name for name, values in attrs.items() if len(set(values)) <= ANNOTATION_CROSS_VALUES]
    by_attr: dict[str, dict[str, int]] = {name: {} for name in attrs}
    cross: dict[str, dict[str, dict[str, int]]] = {name: {} for name in cross_attrs}
    for r, ops in enumerate(out.queries):
        names = ann.labels_of(r, len(ops)) if ann.ops else []
        for name in set(names):
            label_requests[name] = label_requests.get(name, 0) + 1
        for i, (k, _) in enumerate(ops):
            label = names[i] if names else None
            if label is not None:
                labels[label] = labels.get(label, 0) + 1
            for name, values in attrs.items():
                v = values[k] if k < len(values) else "-"
                by_attr[name][v] = by_attr[name].get(v, 0) + 1
                if label is not None and name in cross:
                    row = cross[name].setdefault(label, {})
                    row[v] = row.get(v, 0) + 1
    return {"requests": len(out.queries), "labels": labels, "label_requests": label_requests,
            "attrs": by_attr, "cross": cross, "problems": len(problems), "problem_examples": problems[:3]}


def has_annotations(text: str) -> bool:
    return any(line.startswith(("@paper ", "@ops ")) for line in text.splitlines())


def _annotations_job(job: tuple[str, int]) -> tuple[int, dict]:
    run, seed = job
    run_dir = Path(run)
    inp = load_input(seed)
    path, err = out_path(run_dir, seed), err_path(run_dir, seed)
    out = parse_output(inp, path.read_text(errors="replace") if path.exists() else "")
    ann = parse_annotations(err.read_text(errors="replace") if err.exists() else "", inp.k)
    return seed, annotation_metrics(out, ann)


def run_annotations(run_dir: Path, processes: int | None = None) -> dict[int, dict]:
    """Per-seed annotation_metrics of a run, cached in runs/<run-id>/annotations.json ({} if the first
    err files have no `@paper` / `@ops` line: a solution that does not print its structure)."""
    cache = run_dir / "annotations.json"
    result_mtime = (run_dir / "result.json").stat().st_mtime
    if cache.exists() and cache.stat().st_mtime >= result_mtime:
        try:
            data = json.loads(cache.read_text())
            if data.get("version") == ANNOTATIONS_VERSION:
                return {int(s): m for s, m in data["cases"].items()}
        except (OSError, ValueError, KeyError):
            pass
    seeds = sorted(run_cases(run_dir))
    probe = [err_path(run_dir, s) for s in seeds[:3]]
    if not any(p.exists() and has_annotations(p.read_text(errors="replace")) for p in probe):
        return {}
    jobs = [(str(run_dir), s) for s in seeds]
    procs = processes or min(8, os.cpu_count() or 1)
    if procs > 1 and len(jobs) > 8:
        import multiprocessing
        with multiprocessing.get_context("fork").Pool(procs) as pool:
            computed = dict(pool.map(_annotations_job, jobs, chunksize=4))
    else:
        computed = dict(map(_annotations_job, jobs))
    write_json_atomic(cache, {"version": ANNOTATIONS_VERSION, "cases": {str(s): m for s, m in computed.items()}})
    return computed


def _metrics_job(job: tuple[str, int]) -> tuple[int, dict]:
    run, seed = job
    run_dir = Path(run)
    inp = load_input(seed)
    path = out_path(run_dir, seed)
    text = path.read_text(errors="replace") if path.exists() else ""
    m = case_metrics(inp, parse_output(inp, text))
    err = err_path(run_dir, seed)
    m["stderr"] = stderr_stats(err.read_text(errors="replace")) if err.exists() else {}
    return seed, m


def run_metrics(run_dir: Path, processes: int | None = None) -> dict[int, dict]:
    """Per-seed metrics of a run, cached in runs/<run-id>/metrics.json.

    Each entry also has judge_score (from result.json) and execution_time. When result.json is newer
    than the cache (e.g. seeds added by scripts/pahcer_run.py --extend), the cached entries of the
    cases whose score and time did not change are kept, and only the other cases are replayed.
    """
    cache = run_dir / "metrics.json"
    result_mtime = (run_dir / "result.json").stat().st_mtime
    cached = {}
    if cache.exists():
        try:
            data = json.loads(cache.read_text())
            if data.get("version") == METRICS_VERSION:
                cached = {int(s): m for s, m in data["cases"].items()}
                if cache.stat().st_mtime >= result_mtime:
                    return cached
        except (OSError, ValueError, KeyError):
            cached = {}
    cases = run_cases(run_dir)
    kept = {s: m for s, m in cached.items() if s in cases and m.get("judge_score") == cases[s]["score"]
            and m.get("execution_time") == cases[s]["execution_time"]}
    jobs = [(str(run_dir), s) for s in sorted(cases) if s not in kept]
    procs = processes or min(8, os.cpu_count() or 1)
    if procs > 1 and len(jobs) > 8:
        import multiprocessing
        with multiprocessing.get_context("fork").Pool(procs) as pool:
            computed = dict(pool.map(_metrics_job, jobs, chunksize=4))
    else:
        computed = dict(map(_metrics_job, jobs))
    for s, m in computed.items():
        m["judge_score"] = cases[s]["score"]
        m["execution_time"] = cases[s]["execution_time"]
    computed = dict(sorted({**kept, **computed}.items()))
    write_json_atomic(cache, {"version": METRICS_VERSION, "cases": {str(s): m for s, m in computed.items()}})
    return computed
