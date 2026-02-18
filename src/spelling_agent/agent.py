"""Autonomous spelling correction agent for .txt files."""

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from spellchecker import SpellChecker


@dataclass
class CorrectionResult:
    file_path: str
    original_word: str
    corrected_word: str
    line_number: int
    column: int


@dataclass
class FileReport:
    file_path: str
    corrections: list[CorrectionResult] = field(default_factory=list)
    error: str | None = None


class SpellingAgent:
    def __init__(self, language: str = "en", custom_words: list[str] | None = None):
        self.spell = SpellChecker(language=language)
        if custom_words:
            self.spell.word_frequency.load_words(custom_words)

    def _extract_words(self, text: str) -> list[tuple[str, int, int]]:
        words: list[tuple[str, int, int]] = []
        for line_idx, line in enumerate(text.splitlines(), start=1):
            for match in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)?", line):
                words.append((match.group(), line_idx, match.start()))
        return words

    def _should_skip(self, word: str) -> bool:
        if len(word) <= 1:
            return True
        if word.isupper() and len(word) >= 2:
            return True
        return False

    def _best_candidate(self, word: str) -> str | None:
        candidates = self.spell.candidates(word)
        if not candidates:
            return None

        candidates.discard(word)
        if not candidates:
            return None

        min_dist = min(self._edit_distance(word, c) for c in candidates)
        closest = [c for c in candidates if self._edit_distance(word, c) == min_dist]

        if len(closest) == 1:
            return closest[0]

        return max(closest, key=lambda c: self.spell.word_usage_frequency(c))

    @staticmethod
    def _edit_distance(a: str, b: str) -> int:
        m, n = len(a), len(b)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, n + 1):
                temp = dp[j]
                if a[i - 1] == b[j - 1]:
                    dp[j] = prev
                else:
                    dp[j] = 1 + min(prev, dp[j], dp[j - 1])
                prev = temp
        return dp[n]

    def correct_text(self, text: str) -> tuple[str, list[CorrectionResult]]:
        corrections: list[CorrectionResult] = []
        words = self._extract_words(text)

        replacements: list[tuple[int, int, str, str]] = []

        for word, line_num, col in words:
            if self._should_skip(word):
                continue

            lower_word = word.lower()
            misspelled = self.spell.unknown([lower_word])

            if lower_word in misspelled:
                candidate = self._best_candidate(lower_word)
                if candidate is None or candidate == lower_word:
                    continue

                if word[0].isupper():
                    candidate = candidate.capitalize()
                if word.isupper():
                    candidate = candidate.upper()

                replacements.append((line_num, col, word, candidate))
                corrections.append(
                    CorrectionResult(
                        file_path="",
                        original_word=word,
                        corrected_word=candidate,
                        line_number=line_num,
                        column=col,
                    )
                )

        if not replacements:
            return text, corrections

        lines = text.splitlines(keepends=True)
        for line_num, col, original, replacement in reversed(replacements):
            idx = line_num - 1
            line = lines[idx]
            lines[idx] = line[:col] + replacement + line[col + len(original) :]

        return "".join(lines), corrections

    def process_file(self, file_path: str, dry_run: bool = False) -> FileReport:
        report = FileReport(file_path=file_path)

        try:
            path = Path(file_path)
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            report.error = str(exc)
            return report

        corrected_text, corrections = self.correct_text(text)

        for correction in corrections:
            correction.file_path = file_path

        report.corrections = corrections

        if corrections and not dry_run:
            path.write_text(corrected_text, encoding="utf-8")

        return report

    def process_directory(
        self, directory: str, recursive: bool = True, dry_run: bool = False
    ) -> list[FileReport]:
        pattern = os.path.join(directory, "**", "*.txt") if recursive else os.path.join(directory, "*.txt")
        txt_files = sorted(glob.glob(pattern, recursive=recursive))

        if not txt_files:
            print(f"No .txt files found in: {directory}")
            return []

        reports: list[FileReport] = []
        for file_path in txt_files:
            report = self.process_file(file_path, dry_run=dry_run)
            reports.append(report)

        return reports


def format_report(reports: list[FileReport]) -> str:
    lines: list[str] = []
    total_corrections = 0

    for report in reports:
        if report.error:
            lines.append(f"\n[ERROR] {report.file_path}: {report.error}")
            continue

        if not report.corrections:
            lines.append(f"\n[OK] {report.file_path} - no spelling errors found")
            continue

        lines.append(f"\n[CORRECTED] {report.file_path} - {len(report.corrections)} correction(s):")
        for c in report.corrections:
            lines.append(f"  Line {c.line_number}, Col {c.column}: '{c.original_word}' -> '{c.corrected_word}'")
        total_corrections += len(report.corrections)

    lines.append(f"\n--- Summary ---")
    lines.append(f"Files scanned: {len(reports)}")
    lines.append(f"Total corrections: {total_corrections}")
    errors = sum(1 for r in reports if r.error)
    if errors:
        lines.append(f"Files with errors: {errors}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="spelling-agent",
        description="Autonomous spelling correction agent for .txt files",
    )
    parser.add_argument(
        "path",
        nargs="+",
        help="Path(s) to .txt file(s) or directory containing .txt files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report errors without modifying files",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not search directories recursively",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language for spell checking (default: en)",
    )
    parser.add_argument(
        "--add-words",
        nargs="*",
        default=None,
        help="Additional words to add to the dictionary",
    )

    args = parser.parse_args()

    agent = SpellingAgent(language=args.language, custom_words=args.add_words)
    all_reports: list[FileReport] = []

    for path_str in args.path:
        path = Path(path_str)
        if path.is_file():
            if not path.suffix == ".txt":
                print(f"Skipping non-.txt file: {path}")
                continue
            report = agent.process_file(str(path), dry_run=args.dry_run)
            all_reports.append(report)
        elif path.is_dir():
            reports = agent.process_directory(
                str(path),
                recursive=not args.no_recursive,
                dry_run=args.dry_run,
            )
            all_reports.extend(reports)
        else:
            print(f"Path not found: {path}")

    if all_reports:
        output = format_report(all_reports)
        print(output)

    has_corrections = any(r.corrections for r in all_reports)
    mode = "DRY RUN" if args.dry_run else "APPLIED"
    if has_corrections:
        print(f"\nMode: {mode}")

    sys.exit(0)


if __name__ == "__main__":
    main()
