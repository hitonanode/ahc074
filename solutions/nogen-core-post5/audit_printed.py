"""保存出力の所有色を物理窓で再検査する。共有flockの下で実行する。"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import replay

run = replay.resolve_run(sys.argv[1])
checked = exceptions = cases = 0
for output in sorted((run / 'out').glob('*.txt')):
    seed = int(output.stem)
    # Only the declared product patterns are needed; do not read order lines.
    with (replay.main_root() / 'tools' / 'in' / f'{seed:04d}.txt').open() as stream:
        n, k, p, _ = map(int, stream.readline().split())
        patterns = [stream.readline().strip() for _ in range(p)]
    with output.open() as stream:
        sheets = [stream.readline().strip() for _ in range(k)]
    annotation = replay.parse_annotations((run / 'err' / output.name).read_text(), k)
    owners = annotation.papers['targets']
    assert sheets[0] == '.' * 63 + '1', (seed, 'cap')
    assert owners[0] == '-'
    for paper in range(1, k):
        assert len(sheets[paper]) == n
        product_ids = [int(x) for x in owners[paper].split(',')]
        assert product_ids and all(0 <= u < p for u in product_ids)
        for window, color in enumerate(sheets[paper]):
            assert color in '.01'
            if color == '.':
                continue
            desired = {patterns[u][window] for u in product_ids}
            if window == 63 and len(desired) == 2:
                assert len(product_ids) == 2 and color == '0', (seed, paper, window)
                exceptions += 1
            else:
                assert desired == {color}, (seed, paper, window, product_ids)
        checked += 1
    cases += 1
print(f'cases = {cases}\nproduct_papers = {checked}\ncap_pair_exceptions = {exceptions}\nviolations = 0')
