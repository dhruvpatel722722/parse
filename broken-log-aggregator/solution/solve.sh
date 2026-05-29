#!/bin/bash
# Optimize the query engine with proper indexing

cat > /app/engine/index.py << 'PYTHON'
import json
import bisect
from collections import defaultdict
from data import load_records

class SearchIndex:
    """An optimized search index with inverted indices and sorted arrays."""
    
    def __init__(self):
        self.records = load_records()
        self._build_indices()
    
    def _build_indices(self):
        """Build inverted index for tags and sorted arrays for score/timestamp."""
        # Inverted index: tag -> set of record indices
        self.tag_index = defaultdict(set)
        for i, rec in enumerate(self.records):
            for tag in rec["tags"]:
                self.tag_index[tag].add(i)
        
        # Score index: sorted list of (score, index) for binary search
        self.score_sorted = sorted(range(len(self.records)), key=lambda i: self.records[i]["score"])
        self.scores = [self.records[i]["score"] for i in self.score_sorted]
        
        # Timestamp index: sorted list of (timestamp, index) for binary search
        self.time_sorted = sorted(range(len(self.records)), key=lambda i: self.records[i]["timestamp"])
        self.timestamps = [self.records[i]["timestamp"] for i in self.time_sorted]
    
    def get_all_indices(self):
        """Return set of all record indices."""
        return set(range(len(self.records)))
    
    def get_indices_by_tag(self, tag):
        """Return set of indices for records with given tag."""
        return self.tag_index.get(tag, set())
    
    def get_indices_in_score_range(self, min_score, max_score):
        """Return set of indices for records in score range using binary search."""
        lo = bisect.bisect_left(self.scores, min_score)
        hi = bisect.bisect_right(self.scores, max_score)
        return set(self.score_sorted[lo:hi])
    
    def get_indices_in_time_range(self, start, end):
        """Return set of indices for records in timestamp range using binary search."""
        lo = bisect.bisect_left(self.timestamps, start)
        hi = bisect.bisect_right(self.timestamps, end)
        return set(self.time_sorted[lo:hi])
    
    def get_records_by_indices(self, indices):
        """Return records for given indices."""
        return [self.records[i] for i in indices]
PYTHON

cat > /app/engine/query.py << 'PYTHON'
from index import SearchIndex

class QueryEngine:
    """Execute queries against the search index using set intersection."""
    
    def __init__(self):
        self.index = SearchIndex()
    
    def execute(self, query):
        """Execute a query dict and return matching records."""
        candidate_sets = []
        
        # Filter by tags (AND logic: intersect sets for each tag)
        if "tags_all" in query:
            for tag in query["tags_all"]:
                candidate_sets.append(self.index.get_indices_by_tag(tag))
        
        # Filter by tags (OR logic: union of tag sets)
        if "tags_any" in query:
            union = set()
            for tag in query["tags_any"]:
                union.update(self.index.get_indices_by_tag(tag))
            candidate_sets.append(union)
        
        # Filter by score range
        if "min_score" in query or "max_score" in query:
            min_s = query.get("min_score", float("-inf"))
            max_s = query.get("max_score", float("inf"))
            candidate_sets.append(self.index.get_indices_in_score_range(min_s, max_s))
        
        # Filter by timestamp range
        if "start_time" in query or "end_time" in query:
            start = query.get("start_time", "")
            end = query.get("end_time", "9999-12-31T23:59:59Z")
            candidate_sets.append(self.index.get_indices_in_time_range(start, end))
        
        # Intersect all candidate sets
        if candidate_sets:
            result_indices = candidate_sets[0]
            for s in candidate_sets[1:]:
                result_indices = result_indices.intersection(s)
        else:
            result_indices = self.index.get_all_indices()
        
        # Get actual records
        results = self.index.get_records_by_indices(result_indices)
        
        # Sort
        if "sort_by" in query:
            field = query["sort_by"]
            reverse = query.get("sort_desc", False)
            results.sort(key=lambda r: r[field], reverse=reverse)
        
        # Pagination
        offset = query.get("offset", 0)
        limit = query.get("limit", len(results))
        results = results[offset:offset + limit]
        
        return results
PYTHON

# Run benchmark
python /app/engine/bench.py
