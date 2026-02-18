# Spelling Agent

An autonomous agent that detects and corrects spelling errors in `.txt` files.

## Installation

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install .
```

## Usage

### Correct a single file

```bash
python -m spelling_agent.agent myfile.txt
```

### Correct all .txt files in a directory (recursive)

```bash
python -m spelling_agent.agent ./documents/
```

### Dry run (report errors without modifying files)

```bash
python -m spelling_agent.agent --dry-run ./documents/
```

### Multiple paths

```bash
python -m spelling_agent.agent file1.txt file2.txt ./more_files/
```

### Add custom words to the dictionary

```bash
python -m spelling_agent.agent --add-words kubectl nginx pytest ./docs/
```

### Non-recursive directory scan

```bash
python -m spelling_agent.agent --no-recursive ./documents/
```

### If installed as a package

```bash
spelling-agent myfile.txt
spelling-agent --dry-run ./documents/
```

## Features

- Scans `.txt` files for spelling errors
- Corrects misspellings in-place (or dry-run to preview)
- Preserves original casing (Title Case, UPPERCASE)
- Skips acronyms (all-caps words)
- Recursive directory scanning
- Custom dictionary words via `--add-words`
- Detailed correction report with line/column numbers

## Output Example

```
[OK] clean.txt - no spelling errors found

[CORRECTED] sample.txt - 5 correction(s):
  Line 1, Col 0: 'Ths' -> 'The'
  Line 1, Col 9: 'smple' -> 'simple'
  Line 2, Col 16: 'wonderfull' -> 'wonderful'
  Line 3, Col 11: 'corect' -> 'correct'
  Line 3, Col 34: 'automaticaly' -> 'automatically'

--- Summary ---
Files scanned: 2
Total corrections: 5

Mode: APPLIED
```

## How It Works

1. The agent scans the provided path(s) for `.txt` files
2. Each file is tokenized into words while tracking line/column positions
3. Words are checked against a dictionary (pyspellchecker)
4. For misspelled words, the agent selects the best correction by:
   - Finding all candidates at the minimum edit distance
   - Breaking ties using word frequency (most common word wins)
5. Corrections are applied in-place, preserving the original text structure
6. A detailed report is printed showing all changes made
