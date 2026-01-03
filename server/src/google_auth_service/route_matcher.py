"""
Route Matcher - URL pattern matching for service configuration.

Provides flexible URL matching capabilities for determining which
routes require auth, are optional, or are public.

Supported patterns:
- Exact match: "/api/users"
- Prefix match: "/api/*" (matches /api/anything)
- Wildcard match: "/api/users/*/posts" (matches /api/users/123/posts)
- Deep wildcard: "/api/**" (matches /api/users/123/posts/456)
- Regex match: "^/api/v[0-9]+/.*$"

Usage:
    matcher = RouteMatcher(["/api/*", "/admin/**"])
    
    if matcher.matches("/api/users"):
        # Route matches
        pass
"""

import re
import logging
from typing import List, Set, Optional, Pattern
from fnmatch import fnmatch

logger = logging.getLogger(__name__)


class RouteMatcher:
    """
    Flexible URL pattern matcher for route configuration.
    
    Supports exact matches, glob patterns, and regex patterns.
    """
    
    def __init__(self, patterns: List[str]):
        """
        Initialize route matcher with patterns.
        
        Args:
            patterns: List of URL patterns to match
        """
        self.patterns = patterns
        self._exact_matches: Set[str] = set()
        self._prefix_patterns: List[str] = []
        self._glob_patterns: List[str] = []
        self._regex_patterns: List[Pattern] = []
        
        # Classify patterns for performance
        self._classify_patterns()
    
    def _classify_patterns(self) -> None:
        """
        Classify patterns by type for optimal matching performance.
        
        Order of matching:
        1. Exact matches (fastest - O(1))
        2. Prefix patterns (fast - string startswith)
        3. Glob patterns (medium - fnmatch)
        4. Regex patterns (slowest - regex matching)
        """
        for pattern in self.patterns:
            # Empty pattern
            if not pattern:
                continue
            
            # Regex pattern (starts with ^)
            if pattern.startswith("^"):
                try:
                    compiled = re.compile(pattern)
                    self._regex_patterns.append(compiled)
                    logger.debug(f"Classified as regex: {pattern}")
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                continue
            
            # Glob pattern (contains * or ?)
            if "*" in pattern or "?" in pattern:
                # Simple prefix wildcard: /api/*
                if pattern.endswith("/*") and "*" not in pattern[:-2]:
                    prefix = pattern[:-2]  # Remove /*
                    self._prefix_patterns.append(prefix)
                    logger.debug(f"Classified as prefix: {prefix}")
                else:
                    # Complex glob: /api/*/users or /api/**
                    self._glob_patterns.append(pattern)
                    logger.debug(f"Classified as glob: {pattern}")
                continue
            
            # Exact match
            self._exact_matches.add(pattern)
            logger.debug(f"Classified as exact: {pattern}")
    
    def matches(self, path: str) -> bool:
        """
        Check if a URL path matches any configured pattern.
        
        Args:
            path: URL path to check (e.g., "/api/users/123")
        
        Returns:
            True if path matches any pattern, False otherwise
        """
        # Strip query parameters and fragments
        path = path.split("?")[0].split("#")[0]
        
        # Normalize path (remove trailing slash unless it's just "/")
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        
        # 1. Exact match (O(1))
        if path in self._exact_matches:
            return True
        
        # 2. Prefix match (O(n) but fast)
        for prefix in self._prefix_patterns:
            if path.startswith(prefix + "/") or path == prefix:
                return True
        
        # 3. Glob match (O(n))
        for pattern in self._glob_patterns:
            if fnmatch(path, pattern):
                return True
        
        # 4. Regex match (O(n) but slower)
        for regex in self._regex_patterns:
            if regex.match(path):
                return True
        
        return False
    
    def get_matching_pattern(self, path: str) -> Optional[str]:
        """
        Get the first pattern that matches the given path.
        
        Useful for debugging or determining which rule matched.
        
        Args:
            path: URL path to check
        
        Returns:
            Matching pattern string or None
        """
        # Strip query parameters and fragments
        path = path.split("?")[0].split("#")[0]
        
        # Normalize path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        
        # Exact match
        if path in self._exact_matches:
            return path
        
        # Prefix match
        for prefix in self._prefix_patterns:
            if path.startswith(prefix + "/") or path == prefix:
                return prefix + "/*"
        
        # Glob match
        for pattern in self._glob_patterns:
            if fnmatch(path, pattern):
                return pattern
        
        # Regex match
        for regex in self._regex_patterns:
            if regex.match(path):
                return regex.pattern
        
        return None
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"RouteMatcher("
            f"exact={len(self._exact_matches)}, "
            f"prefix={len(self._prefix_patterns)}, "
            f"glob={len(self._glob_patterns)}, "
            f"regex={len(self._regex_patterns)})"
        )


class RouteConfig:
    """
    Route configuration helper for services.
    
    Manages multiple route lists (required, optional, public) with
    precedence and exclusion logic.
    """
    
    def __init__(
        self,
        required: List[str] = None,
        optional: List[str] = None,
        public: List[str] = None,
    ):
        """
        Initialize route configuration.
        
        Args:
            required: Routes that REQUIRE the service (e.g., auth required)
            optional: Routes where service is OPTIONAL (e.g., auth optional)
            public: Routes that are PUBLIC (e.g., no auth needed)
        
        Precedence: public > required > optional (for conflict resolution)
        """
        self.required_matcher = RouteMatcher(required or [])
        self.optional_matcher = RouteMatcher(optional or [])
        self.public_matcher = RouteMatcher(public or [])
    
    def is_required(self, path: str) -> bool:
        """
        Check if service is REQUIRED for this path.
        
        Returns False if path is public (public takes precedence).
        """
        if self.is_public(path):
            return False
        return self.required_matcher.matches(path)
    
    def is_optional(self, path: str) -> bool:
        """
        Check if service is OPTIONAL for this path.
        
        Returns False if path is public or required.
        """
        if self.is_public(path):
            return False
        if self.required_matcher.matches(path):
            return False
        return self.optional_matcher.matches(path)
    
    def is_public(self, path: str) -> bool:
        """
        Check if path is PUBLIC (service not needed).
        
        Public takes highest precedence.
        """
        return self.public_matcher.matches(path)
    
    def requires_service(self, path: str) -> bool:
        """
        Check if service is needed (required OR optional) for this path.
        
        Returns False if path is not matched by any configuration.
        """
        return self.is_required(path) or self.is_optional(path)


__all__ = [
    "RouteMatcher",
    "RouteConfig",
]
