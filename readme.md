Nixtat is a script for quick and simple nix store space occupation analysis

It scans your `/nix/store` (or any specified path), aggregates package sizes by name (with or without versions), and displays a sorted, human-readable table of the results.

# Features

- **Smart Aggregation**: Automatically groups packages by name (e.g., `python3-3.10` and `python3-3.11` are grouped under `python3` unless configured otherwise).
- **Rich Output**: Uses the `rich` library for beautiful terminal tables, progress bars, and color coding.
- **Flexible Sorting**: Sort by total size, occurrence count, or package name.
- **Filtering**: Automatically ignores `.drv` manifests and non-directory files.
- **Custom Paths**: Can analyze alternative store locations.
- **Script Friendly**: Includes a `--simplify` mode for machine-readable output.

# Installation & Usage

## Using Nix Flakes

Directly from the repository:

```bash
nix run github:jrodez/nixtat
```

or in a nix flake:

```nix
inputs.nixtat.url = "github:jrodez/nixtat";
```


## Using Nix (Legacy)

```bash
nix-build && ./result/bin/nixtat.py
```

# Options

| Option | Description |
|--------|-------------|
| `-H`, `--human-readable` | **Default**. Display sizes in human-readable format with headers and progress bar. |
| `--simplify` | Disable rich output. Use simple text format (name size count % %cumul). |
| `--with-version` | Keep version numbers in package names (e.g., `go-1.20` instead of `go`). |
| `--sort {size,count,name}` | Column to sort by. Default is `size`. |
| `-r`, `--reverse` | Reverse the sort order. |
| `-n N` | Limit output to N lines. |
| `--full` | Display all lines (disables auto-truncation based on terminal height). |
| `--path PATH` | Path to the nix store (default: `/nix/store`). |
| `-v`, `--verbose` | Display errors (like permission denied) as they occur. |

# Examples

**View top disk consumers:**
```bash
nixtat.py
```

**View top consumers keeping versions distinct:**
```bash
nixtat.py --with-version
```

**Sort by number of store paths (occurrences):**
```bash
nixtat.py --sort count
```
