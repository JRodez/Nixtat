#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import argparse
import glob
from collections import defaultdict

# Configuration des arguments, -h est réservé donc on utilise --human-readable et -H
parser = argparse.ArgumentParser(description="Analyze disk space used by packages in a nix store.")
parser.add_argument('--with-version', action='store_true', help="Keep version numbers in package names.")
parser.add_argument('-H', '--human-readable', action='store_true', help="Display sizes in human-readable format, add headers and a progress bar.")
parser.add_argument('-v', '--verbose', action='store_true', help="Display errors as they occur.")
parser.add_argument('--sort', choices=['size', 'count', 'name'], default='size', help="Sort column.")
parser.add_argument('-r', '--reverse', action='store_true', help="Reverse sort order.")
parser.add_argument('-n', type=int, help="Number of lines to display (mode -H).")
parser.add_argument('--full', action='store_true', help="Display all lines (mode -H).")
parser.add_argument('--path', default='/nix/store', help="Path to the nix store (default: /nix/store).")
args = parser.parse_args()

# Rich management for display (only if -H is enabled)
USE_RICH = args.human_readable
if USE_RICH:
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, MofNCompleteColumn
    except ImportError:
        print("Error: The 'rich' module is required for the -H option. Install it with 'pip install rich' or remove the -H option.", file=sys.stderr)
        sys.exit(1)

def get_human_size(size_in_kb):
    """Converts a size in KB to a readable unit (MB, GB)."""
    for unit in ['KB', 'MB', 'GB', 'TB']:
        if size_in_kb < 1024.0:
            return f"{size_in_kb:.2f} {unit}"
        size_in_kb /= 1024.0
    return f"{size_in_kb:.2f} PB"

def parse_package_name(path, keep_version):
    """
        Extracts the package name from the full path.
        Example: /nix/store/hash-go-1.25.4 -> go-1.25.4 (or 'go' if keep_version is False)
    """
    base_name = os.path.basename(path)
    
    # Regex 1: Remove the hash (32 alphanumeric characters followed by a dash at the beginning)
    # Nix store hash is in base32 (a-z0-9)
    match_hash = re.match(r'^[a-z0-9]{32}-(.*)$', base_name)
    
    if not match_hash:
        return base_name # Fallback if the format is not standard
    
    name_with_version = match_hash.group(1)
    
    if keep_version:
        return name_with_version
    
    # Regex 2: Remove the version
    # Look for the last dash followed by a digit, which usually indicates the start of the version.
    # Ex: go-1.25.4 -> go
    # Ex: python3-3.9 -> python3
    match_version = re.match(r"^(.*?)(?:-[0-9].*)?$", name_with_version)
    if match_version:
        return match_version.group(1)
    
    return name_with_version

def main():
    store_path = args.path
    if not os.path.exists(store_path):
        print(f"Error: The directory {store_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    # Retrieve the list of directories
    # We use glob to list, but we will pass these paths to `du`
    try:
        all_paths = glob.glob(os.path.join(store_path, '*'))
        # Keep only directories
        all_paths = [p for p in all_paths if os.path.isdir(p)]
    except Exception as e:
        print(f"Error reading the store: {e}", file=sys.stderr)
        sys.exit(1)

    # Dictionary for aggregation: { "package_name": {"size": 0, "count": 0} }
    stats = defaultdict(lambda: {"size": 0, "count": 0})
    encountered_errors = set()

    # Process in batches to avoid "Argument list too long" with subprocess
    CHUNK_SIZE = max(100, min(1000, len(all_paths) // 100))  # Adjusts chunk size based on total size
    
    # Initialize progress bar if necessary
    progress = None
    task_id = None
    console_err = None

    if USE_RICH:
        console_err = Console(stderr=True)
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console_err,
            transient=True
        )
        progress.start()
        task_id = progress.add_task("Analyzing the store", total=len(all_paths))

    for i in range(0, len(all_paths), CHUNK_SIZE):
        chunk = all_paths[i:i + CHUNK_SIZE]
        
        if not chunk:
            continue

        # Call `du -s -k` (in Kilobytes for consistency)
        # We use -k to force KB, as the default behavior of du varies by OS
        cmd = ['du', '-s', '-k'] + chunk
        
        # Execute du and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.stderr:
            for line in result.stderr.splitlines():
                encountered_errors.add(line)
                if args.verbose:
                    if progress:
                        progress.console.print(line, style="red")
                    else:
                        print(line, file=sys.stderr)
        
        for line in result.stdout.splitlines():
            parts = line.split('\t')
            if len(parts) != 2:
                continue
            
            try:
                size_kb = int(parts[0])
            except ValueError:
                continue
            
            path = parts[1]
            
            # Extract and clean the name
            pkg_name = parse_package_name(path, args.with_version)
            
            # Aggregation
            stats[pkg_name]["size"] += size_kb
            stats[pkg_name]["count"] += 1
            
            if progress:
                progress.update(task_id, advance=1)

    if progress:
        progress.stop()

    if encountered_errors:
        print(f"\nError summary ({len(encountered_errors)} error types):", file=sys.stderr)
        for err in sorted(encountered_errors):
            print(f"  {err}", file=sys.stderr)

    # Sort results
    key_map = {
        'size': lambda item: item[1]['size'],
        'count': lambda item: item[1]['count'],
        'name': lambda item: item[0]
    }
    sorted_stats = sorted(stats.items(), key=key_map[args.sort], reverse=args.reverse)

    # Calculate percentages and cumulative values
    total_size = sum(item[1]['size'] for item in sorted_stats)
    cumulative_size = 0
    processed_stats = []
    for name, data in sorted_stats:
        cumulative_size += data['size']
        perc = (data['size'] / total_size * 100) if total_size > 0 else 0
        cum_perc = (cumulative_size / total_size * 100) if total_size > 0 else 0
        processed_stats.append((name, data, perc, cum_perc))

    # Affichage
    if args.human_readable:
        console = Console()
        
        limit = len(sorted_stats)
        if not args.full:
            if args.n is not None:
                limit = args.n
            else:
                limit = int(console.size.height * 0.8)

        special_names_re = re.compile(r"^(source|system-path|nixos($|-.*))")

        table = Table(title="Nix Disk Space Analysis", expand=True, row_styles=["", "on color(236)"])
        table.add_column("Package Name", style="cyan", no_wrap=True)
        table.add_column("Size", justify="right", style="green")
        table.add_column("Occurrences", justify="right", style="magenta")
        table.add_column("%", justify="right", style="blue")
        table.add_column("% Cumul.", justify="right", style="yellow")

        subset = processed_stats[-limit:] if limit > 0 else []
        for name, data, perc, cum_perc in subset:
            row_style = None
            if special_names_re.match(name):
                row_style = "on color(54)"  # Dark magenta background for special packages

            table.add_row(
                name, 
                get_human_size(data['size']), 
                str(data['count']),
                f"{perc:.2f}%",
                f"{cum_perc:.2f}%",
                style=row_style
            )
        
        console.print(table)
    else:
        # Standard format: name size(KB) count % %cumul
        for name, data, perc, cum_perc in processed_stats:
            print(f"{name} {data['size']} {data['count']} {perc:.2f}% {cum_perc:.2f}%")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(0)
