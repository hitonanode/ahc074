# A - Layered Barcode Display

実行時間制限: 2 sec / メモリ制限: 1024 MiB

### Problem Statement

There is a barcode display device with $N$ windows arranged in a horizontal row, and there are $K$ sheets of paper.
The windows are numbered from $0$ to $N-1$, and the sheets from $0$ to $K-1$.
Each sheet has a position corresponding to each window, and all sheets are stacked with these positions aligned to display a barcode.

There are $P$ types of items, and the list of their corresponding barcodes $A_0,\ldots,A_{P-1}$ is given at the beginning.
The barcodes are distinct strings of length $N$ consisting of `0` and `1`.

After receiving this list, you design the pattern of sheet $k$ as a string $S_k$ of length $N$.
Each character is either `0` for white, `1` for black, or `.` for a hole.
A sheet consisting entirely of holes is also allowed.
The patterns cannot be changed after they are designed, and the initial order of the sheets, from top to bottom, is $0,1,\ldots,K-1$.

Window $j$ displays the color of the topmost sheet that does not have a hole at that position.
If there is no such sheet, the window displays white.
This topmost sheet is called the "sheet visible through window $j$."

After you submit the designs, $R$ orders are given one at a time.
For order $r$, you are given the item number $a_r$ and aim to make the displayed barcode match $A_{a_r}$ by repeating the following operation.

- Choose a sheet $k$ that is visible through at least one window and an integer $d$.
  Remove sheet $k$ and reinsert it below the top $d$ sheets among the remaining sheets.
  Here, $0\leq k<K$ and $0\leq d<K$.
  If $d=0$, the sheet is placed at the top; if $d=K-1$, it is placed at the bottom.
  The relative order of all other sheets is preserved.

If the displayed barcode after the sequence of operations does not match $A_{a_r}$, the order is counted as incorrect.
Each incorrect order counts as one error regardless of the number of mismatched windows, and you proceed to the next order whether or not the displayed barcode matches.
The next order is not revealed until the current order has been processed, and the sheet order is carried over between orders.
Process all orders using at most $2K$ operations per order, and minimize the absolute score defined below.

### Scoring

Let $E$ be the number of incorrect orders and $T$ be the total number of operations.
After processing all orders, you obtain the following absolute score:

\[
2KE+T
\]

**The lower the absolute score, the better.**

For each test case, you will obtain a **rank score** according to your rank determined by lower absolute score. The score of the submission is the total rank score for each test case. The rank score is calculated as follows, and the higher the rank score, the better.

Let $n_{submit}$ be the number of contestants with submissions, $n_{lose}$ be the number of contestants who received an absolute score lower than yours, and $n_{tie}$ be the number of other contestants who received an absolute score equal to yours. Then your rank in this test case is determined as $r=n_{lose}+0.5 n_{tie}$, and your rank score is $\mathrm{round}(10^9\times (1-\frac{r}{n_{submit}}))$.

The final ranking will be determined by the system test with more inputs which will be run after the contest is over.
In both the provisional/system test, if your submission produces illegal output or exceeds the time limit for some test cases, only the rank score for those test cases will be zero.
The system test will be performed only for **the last submission which received a result other than CE** .
Be careful not to make a mistake in the final submission.

#### Number of test cases

- Provisional test: 50
- System test: 2000. We will publish [seeds.txt](https://img.atcoder.jp/ahc074/seeds.txt) (sha256=9562a1597447a1116b5b4b869d74b3598ce13bc33b1ed8bd9ac1ee9df33d92e7) after the contest is over.

#### About relative evaluation system

In both the provisional/system test, the standings will be calculated using only the last submission which received a result other than CE .

The scores shown in the standings are relative, and whenever a new submission arrives, all relative scores are recalculated.
On the other hand, the score for each submission shown on the submissions page is the sum of the absolute score for each test case, and the relative scores are not shown.
In order to know the relative score of submission other than the latest one in the current standings, you need to resubmit it.
If your submission produces illegal output or exceeds the time limit for some test cases, the score shown on the submissions page will be 0, but the standings show the sum of the rank scores for the test cases that were answered correctly.

#### About execution time

Execution time may vary slightly from run to run.
In addition, since system tests simultaneously perform a large number of executions, it has been observed that execution time increases by several percent compared to provisional tests.
For these reasons, submissions that are very close to the time limit may result in TLE in the system test.
Please measure the execution time in your program to terminate the process, or have enough margin in the execution time.

### Input and Output

This is a reactive problem.
First, the following initial information is given from Standard Input:

```
N K P R
A_0
\vdots
A_{P-1}
```

In all test cases, $N=64$, $K=192$, $P=256$, and $R=1024$.
Each $A_v$ contains exactly $32$ occurrences of `1`.

First, output the sheet designs to Standard Output in the following format:

```
S_0
\vdots
S_{K-1}
```

Then, process the following query $R$ times.
In the $r$-th query, the item number $a_r$ is given from Standard Input in the following format:

```
a_r
```

Let $m$ be the number of operations, and let $k_i$ and $d_i$ be the sheet and insertion position chosen for the $i$-th operation, respectively.
Output them to Standard Output in the following format:

```
m
k_0 d_0
\vdots
k_{m-1} d_{m-1}
```

Here, $0\leq m\leq 2K$.
If you perform no operations, output only `0`.
After the operations are performed in order, the error count increases by one if the displayed barcode does not match $A_{a_r}$.
Terminate your program after outputting the sequence of operations for the last order.
If the last order is processed normally, no further input is given by the judge.
If an invalid design, operation, or output format is detected, `-1` is given and your solution is judged as invalid.
Terminate your program immediately upon receiving `-1`.
Ending your output before processing all orders or producing extra output after the interaction ends is also judged as invalid.

**Each output must be followed by a newline, and you must flush standard output.**
Otherwise, the submission may be judged as TLE.

#### Example

For illustration, consider a small example with $N=4,K=3,P=4,R=3$, which is smaller than the actual constraints.
The animation at the end of the story shows the changes in the sheet order and display for this example.

| $t$ | Input | Output |
| --- | --- | --- |
| Initial information | ```
4 3 4 3
1001
1100
0011
0110
``` |  |
| Designs |  | ```
10.1
1100
0.1.
``` |
| $0$ | ```
0
``` | ```
0
``` |
| $1$ | ```
1
``` | ```
1
0 2
``` |
| $2$ | ```
2
``` | ```
1
1 2
``` |

The initial display is `1001`, so no operations are performed for order $0$.
For order $1$, sheet $0$ is moved to the bottom to display `1100`; for order $2$, sheet $1$ is moved to the bottom to display `0011`.

### Sample Program (Python)

The following is a sample solution in Python.
It sets the patterns of sheets $0,\ldots,K-1$ to $A_0,\ldots,A_{K-1}$, respectively.
If $a_r < K$, it repeatedly moves the top sheet to the bottom until the corresponding sheet is at the top; otherwise, it proceeds to the next order without performing any operations.
```
import sys

N, K, P, R = map(int, input().split())
patterns = [input().strip() for _ in range(P)]
for k in range(K):
    print(patterns[k])
sys.stdout.flush()

top = 0
for _ in range(R):
    request = int(input())
    if request == -1:
        sys.exit()
    count = (request - top) % K if request < K else 0
    print(count)
    for _ in range(count):
        print(top, K - 1)
        top = (top + 1) % K
    sys.stdout.flush()
```

[Show example](https://img.atcoder.jp/ahc074/YAAu43G9.html?lang=en&seed=0&output=sample)

### Input Generation

Sample $P$ strings uniformly without replacement from all strings of length $64$ consisting of `0` and `1` with exactly $32$ occurrences of `1`, and assign them to $A_0,\ldots,A_{P-1}$ in the order sampled.
Choose $a_0$ uniformly from $0,\ldots,P-1$.
For $r\geq 1$, choose $a_r$ uniformly from the $P-1$ numbers other than $a_{r-1}$.

### Tools (Input generator, local tester, and visualizer)

- [Web version](https://img.atcoder.jp/ahc074/YAAu43G9.html?lang=en): This is more powerful than the local version providing animations.
- [Local version](https://img.atcoder.jp/ahc074/YAAu43G9.zip): You need a compilation environment of [Rust language](https://www.rust-lang.org/).
  If it does not compile, please try `rustup update`.
  - [Pre-compiled binary for Windows](https://img.atcoder.jp/ahc074/YAAu43G9_windows.zip): If you are not familiar with the Rust language environment, please use this instead.

#### Specification of the input file used by the tools

The input file given to the local tester contains the following information appended to the initial information:

```
a_0
\vdots
a_{R-1}
```

- $a_r$ is the item number for order $r$.
