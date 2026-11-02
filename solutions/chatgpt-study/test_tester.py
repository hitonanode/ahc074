#!/usr/bin/env python3
"""Focused protocol tests for the evaluator port, not solver benchmarks."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTER = ROOT / "tools" / "target" / "release" / "tester"
CASE = "4 3 4 3\n1001\n1100\n0011\n0110\n0\n1\n2\n"


class TesterProtocol(unittest.TestCase):
    def judge(self, output, status=0):
        # These tiny canned solvers consume the initial input and then emit a
        # prewritten transcript. Their score does not represent an AHC solver.
        source = f"import sys; sys.stdout.write({output!r}); sys.stdout.flush(); sys.exit({status})"
        return subprocess.run([str(TESTER), sys.executable, "-c", source], input=CASE,
                              capture_output=True, text=True, timeout=3)

    def test_statement_example(self):
        result = self.judge("10.1\n1100\n0.1.\n0\n1\n0 2\n1\n1 2\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Score = 2\n", result.stderr)

    def test_wrong_display_penalty(self):
        result = self.judge("10.1\n1100\n0.1.\n0\n0\n0\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Score = 12\n", result.stderr)

    def test_hidden_paper(self):
        result = self.judge("1001\n1100\n0.1.\n1\n1 0\n")
        self.assertIn("not visible", result.stderr)
        self.assertIn("Score = 0", result.stderr)

    def test_hole_paper(self):
        result = self.judge("....\n1100\n0.1.\n1\n0 0\n")
        self.assertIn("not visible", result.stderr)

    def test_extra_output(self):
        result = self.judge("10.1\n1100\n0.1.\n0\n1\n0 2\n1\n1 2\nextra\n")
        self.assertIn("Extra output", result.stderr)
        self.assertIn("Score = 0", result.stderr)

    def test_operation_bound(self):
        result = self.judge("10.1\n1100\n0.1.\n7\n")
        self.assertIn("Out of range", result.stderr)

    def test_truncated_output(self):
        result = self.judge("10.1\n1100\n")
        self.assertIn("Unexpected EOF", result.stderr)

    def test_abnormal_exit(self):
        result = self.judge("10.1\n1100\n0.1.\n0\n1\n0 2\n1\n1 2\n", status=4)
        self.assertIn("terminated abnormally", result.stderr)
        self.assertIn("Score = 0", result.stderr)

    def test_stdout_closed_solver_lingers(self):
        output = "10.1\n1100\n0.1.\n0\n1\n0 2\n1\n1 2\n"
        source = (f"import os,sys,time; sys.stdout.write({output!r}); sys.stdout.flush(); "
                  "os.close(1); time.sleep(10)")
        result = subprocess.run([str(TESTER), sys.executable, "-c", source], input=CASE,
                                capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Score = 2", result.stderr)


if __name__ == "__main__":
    unittest.main()
