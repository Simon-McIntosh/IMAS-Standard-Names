from mcp.server.fastmcp import FastMCP
import imas
import re
import functools
import collections
from typing import Dict, List, Any
import time

# Initialize IMAS data structures
tree = imas.dd_zip.dd_etree()
mcp = FastMCP("IMAS")

# Cache for IDS instances to avoid repeated creation
_ids_cache: Dict[str, Any] = {}


# Cache for all IDS names (calculated once)
@functools.lru_cache(maxsize=1)
def _get_all_ids_names() -> List[str]:
    """Get all IDS names (cached)"""
    return [ids.get("name") for ids in tree.findall(".//IDS")]


# Performance metrics
_perf_stats = {"calls": 0, "cache_hits": 0, "total_time": 0.0}


@mcp.tool()
def list_ids():
    """List all the IDSs defined by the IMAS DD."""
    return _get_all_ids_names()


def _get_ids_instance(ids_name: str) -> Any:
    """Get an IDS instance, using cache if available"""
    if ids_name not in _ids_cache:
        _ids_cache[ids_name] = imas.IDSFactory().new(ids_name)
    return _ids_cache[ids_name]


@functools.lru_cache(maxsize=128)
def _get_metadata_cached(ids_path: str) -> dict:
    """Cached version of metadata retrieval"""
    if "/" not in ids_path:
        return {
            "error": f"Invalid path format. Expected 'ids_name/attribute/path', got '{ids_path}'"
        }

    # Split the path into IDS name and attribute path
    parts = ids_path.split("/", 1)
    ids_name = parts[0]
    attribute_path = parts[1] if len(parts) > 1 else ""

    try:
        # Get the cached IDS instance
        ids_instance = _get_ids_instance(ids_name)
        metadata = ids_instance.metadata[attribute_path]

        return {
            "documentation": metadata.documentation
            if metadata.documentation is not None
            else "",
            "units": metadata.units if hasattr(metadata, "units") else "",
            "coordinates": metadata.coordinates
            if hasattr(metadata, "coordinates")
            else "",
            "data_type": metadata.data_type if hasattr(metadata, "data_type") else "",
            "path": ids_path,
        }
    except Exception as e:
        return {"error": f"Error accessing metadata for {ids_path}: {str(e)}"}


@mcp.tool()
def get_documentation(ids_path: str) -> str:
    """Get the documentation for an IDS path.

    Parameters:
    -----------
    ids_path : str
        The path to the IDS in format "ids_name/attribute/path"
        Example: "equilibrium/time_slice/profiles_1d/psi"

    Returns:
    --------
    str
        The documentation string for the specified IDS path
    """
    start_time = time.time()
    _perf_stats["calls"] += 1

    metadata = _get_metadata_cached(ids_path)

    _perf_stats["total_time"] += time.time() - start_time

    if "error" in metadata:
        return metadata["error"]
    return metadata["documentation"] or "No documentation available"


@mcp.tool()
def get_metadata(ids_path: str) -> dict:
    """Get comprehensive metadata for an IDS path.

    Parameters:
    -----------
    ids_path : str
        The path to the IDS in format "ids_name/attribute/path"
        Example: "equilibrium/time_slice/profiles_1d/psi"

    Returns:
    --------
    dict
        A dictionary containing metadata information for the specified IDS path
    """
    start_time = time.time()
    _perf_stats["calls"] += 1

    result = _get_metadata_cached(ids_path)

    _perf_stats["total_time"] += time.time() - start_time
    return result


# Path index data structure
class PathIndex:
    """Efficient index structure for IDS paths"""

    def __init__(self):
        self.paths = []
        self.path_set = set()
        self.prefixes = collections.defaultdict(list)
        self.keywords = collections.defaultdict(list)
        self.segments = collections.defaultdict(list)

    def add_path(self, path: str):
        """Add a path to the index with various lookup optimizations"""
        if path in self.path_set:
            return

        self.paths.append(path)
        self.path_set.add(path)

        # Index path segments for faster lookup
        segments = path.split("/")
        for i, segment in enumerate(segments):
            # Add segment to index with position for context
            self.segments[segment].append((i, path))

            # Add keywords (substrings) for partial matching
            for length in range(3, len(segment) + 1):
                for start in range(0, len(segment) - length + 1):
                    keyword = segment[start : start + length]
                    self.keywords[keyword].append(path)

        # Index prefixes for prefix matching
        for i in range(1, len(path) + 1):
            prefix = path[:i]
            if prefix.endswith("/") or i == len(path):
                self.prefixes[prefix].append(path)

    def search(self, pattern, use_regex=True):
        """Search for paths matching the pattern"""
        if not use_regex:
            # Simple substring search for non-regex patterns
            return [p for p in self.paths if pattern in p]

        try:
            regex = re.compile(pattern)
            return [p for p in self.paths if regex.search(p)]
        except re.error:
            # Fall back to simple substring search if regex is invalid
            return [p for p in self.paths if pattern in p]


# Precomputed paths cache
@functools.lru_cache(maxsize=1)
def _build_path_index() -> PathIndex:
    """Build and cache an optimized index of all available IDS paths"""
    path_index = PathIndex()

    for ids in tree.findall(".//IDS"):
        ids_name = ids.get("name")
        if not ids_name:
            continue

        # Find all elements with attributes
        for elem in ids.findall(".//*[@name]"):
            # Build path from this element up to the IDS
            path_parts = []

            # Walk up the tree to build the path
            current = elem
            while current is not None and current != ids:
                if current.get("name"):
                    path_parts.insert(0, current.get("name"))

                # Navigate to parent - handle lxml or ElementTree
                if hasattr(current, "getparent"):
                    current = current.getparent()
                else:
                    # If using standard ElementTree, we need a different approach
                    # Find the parent by searching from the root
                    found = False
                    for potential_parent in ids.iter():
                        for child in list(potential_parent):
                            if child == current:
                                current = potential_parent
                                found = True
                                break
                        if found:
                            break

                    if not found:
                        break  # No parent found, exit the loop

            if path_parts:
                path = f"{ids_name}/{'/'.join(path_parts)}"
                path_index.add_path(path)

    return path_index


# Backward compatibility function
@functools.lru_cache(maxsize=1)
def _build_all_paths() -> List[str]:
    """Build and cache all available IDS paths"""
    return _build_path_index().paths


# Cache for compiled regex patterns to improve performance
_pattern_cache = functools.lru_cache(maxsize=100)(re.compile)


@mcp.tool()
def find_paths_by_pattern(
    pattern: str, use_regex: bool = True, case_sensitive: bool = True
) -> list:
    """Find all IDS paths that match a given regex pattern using precomputed paths.

    Parameters:
    -----------
    pattern : str
        A regular expression pattern to match against IDS paths
    use_regex : bool, optional
        Whether to interpret the pattern as regex or simple string (default: True)
    case_sensitive : bool, optional
        Whether the search should be case-sensitive (default: True)

    Returns:
    --------
    list
        A list of IDS paths that match the given pattern
    """
    start_time = time.time()
    _perf_stats["calls"] += 1

    try:
        path_index = _build_path_index()

        # Handle non-regex search (faster)
        if not use_regex:
            if not case_sensitive:
                pattern = pattern.lower()
                matching_paths = [p for p in path_index.paths if pattern in p.lower()]
            else:
                matching_paths = [p for p in path_index.paths if pattern in p]
        else:
            # Handle regex search with optimizations
            try:
                # Use cached regex pattern compilation for better performance
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = _pattern_cache(pattern, flags)

                # Attempt to optimize search by looking for common substrings first
                common_substr = _extract_literal_substring(pattern)
                if common_substr and len(common_substr) > 2:
                    # Pre-filter paths using the literal substring for speed
                    candidate_paths = [
                        p for p in path_index.paths if common_substr in p
                    ]
                    matching_paths = [
                        p for p in candidate_paths if compiled_pattern.search(p)
                    ]
                else:
                    # Fall back to full regex search on all paths
                    matching_paths = [
                        p for p in path_index.paths if compiled_pattern.search(p)
                    ]
            except re.error as e:
                return [f"Error in regex pattern: {str(e)}"]

        _perf_stats["total_time"] += time.time() - start_time
        return sorted(matching_paths)

    except Exception as e:
        return [f"Error searching paths: {str(e)}"]


def _extract_literal_substring(pattern: str) -> str:
    """Extract a literal substring from a regex pattern for pre-filtering"""
    # Simple heuristic to find a significant literal part in the regex
    # This won't handle all cases perfectly but helps in common scenarios
    parts = re.split(r"[.*+?()|\[\]{}^$]", pattern)
    parts = [p for p in parts if p and len(p) > 2]
    if parts:
        return max(parts, key=len)
    return ""


@mcp.tool()
def get_performance_stats() -> dict:
    """Get performance statistics about the API usage."""
    path_index = _build_path_index()

    return {
        "calls": _perf_stats["calls"],
        "cache_hits": _perf_stats["calls"] - _get_metadata_cached.cache_info().misses,
        "total_time": f"{_perf_stats['total_time']:.3f} seconds",
        "metadata_cache_info": str(_get_metadata_cached.cache_info()),
        "path_index_size": len(path_index.paths),
        "segment_index_size": len(path_index.segments),
        "keyword_index_size": len(path_index.keywords),
        "regex_cache_info": str(_pattern_cache.cache_info()),
        "ids_instances_cached": len(_ids_cache),
    }


if __name__ == "__main__":
    mcp.run()
