# Fix Plan: Remaining Issues from Multi-Modal Support Review

**Date:** 2026-02-06
**Branch:** `feature/multimodal-support`
**Reviewer:** Claude (Sonnet 4.5)

## Executive Summary

This plan addresses the remaining issues identified in the code review of the multi-modal support feature. Most critical security and reliability issues were already fixed in commits `72e0a75`, `78369ee`, and `0ba1ea7`. This plan focuses on **1 medium-severity issue, 1 low-medium issue, and several low-priority improvements**.

---

## Overview by Priority

| Priority | Issue | Files | Effort |
|----------|-------|-------|--------|
| P1 | Synchronous I/O in TTSProvider | `tts.py` | 15 min |
| P1 | ProcessRegistry race condition | `video.py` | 10 min |
| P3 | Missing concurrency tests | `test_vision.py` | 20 min |
| P4 | Import inconsistency | `telegram.py` | 5 min |
| P4 | Magic number documentation | `video.py` | 5 min |
| P4 | Rate limiter scoping docs | `telegram.py` | 5 min |
| P4 | Backwards compat plan | New file | 10 min |

**Total Estimated Time:** ~70 minutes

---

## Phase 1: Critical Fixes (Priority 1)

### Fix #1: Synchronous I/O in TTSProvider

**File:** `nanobot/providers/tts.py:117-118`

**Problem:** Using synchronous file I/O in an async function blocks the event loop.

**Current Code:**
```python
async def _synthesize_openai(self, text: str, output_path: Path) -> tuple[bool, str | None]:
    # ... validation code ...
    try:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(...)
            response.raise_for_status()

            # Write audio file (BLOCKS EVENT LOOP)
            with open(output_path, "wb") as f:
                f.write(response.content)
```

**Fix:**
```python
async def _synthesize_openai(self, text: str, output_path: Path) -> tuple[bool, str | None]:
    # ... validation code ...
    try:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(...)
            response.raise_for_status()

            # Write audio file asynchronously (non-blocking)
            await asyncio.to_thread(output_path.write_bytes, response.content)
```

**Steps:**
1. Add `import asyncio` at top of file (already there, verify)
2. Replace the `with open()` block with `await asyncio.to_thread()`
3. Run tests: `pytest tests/test_tts.py -v`

**Verification:**
- All TTS tests should pass
- No blocking behavior in async context

---

### Fix #2: ProcessRegistry Thread-Safe Initialization

**File:** `nanobot/agent/video.py:80-85`

**Problem:** Global registry initialization has a race condition.

**Current Code:**
```python
_global_registry: ProcessRegistry | None = None

def get_process_registry() -> ProcessRegistry:
    global _global_registry
    if _global_registry is None:  # RACE: multiple threads could enter
        _global_registry = ProcessRegistry()
    return _global_registry
```

**Fix (Option A - Simplest):**
```python
# Initialize at module import time (no lock needed)
_global_registry: ProcessRegistry = ProcessRegistry()

def get_process_registry() -> ProcessRegistry:
    return _global_registry
```

**Fix (Option B - With locking, consistent with MediaCleanupRegistry):**
```python
import threading
_global_registry: ProcessRegistry | None = None
_lock = threading.Lock()

def get_process_registry() -> ProcessRegistry:
    global _global_registry
    with _lock:
        if _global_registry is None:
            _global_registry = ProcessRegistry()
    return _global_registry
```

**Recommendation:** Use Option A (module-level initialization) because:
1. Simpler (no locking needed)
2. ProcessRegistry has no constructor dependencies
3. Consistent with common Python patterns

**Steps:**
1. Change line 77 from `_global_registry: ProcessRegistry | None = None` to `_global_registry: ProcessRegistry = ProcessRegistry()`
2. Simplify `get_process_registry()` to just return the global
3. Add a test for concurrent initialization (optional but recommended)

**Verification:**
- Existing tests should pass
- ProcessRegistry is always available

---

## Phase 2: Testing Improvements (Priority 3)

### Fix #3: Add Concurrent Access Tests for RateLimiter

**File:** `tests/test_vision.py`

**Add this test class after `TestRateLimiter`:**

```python
class TestRateLimiterConcurrency:
    """Test RateLimiter thread safety under concurrent access."""

    def test_concurrent_access_no_errors(self):
        """Test that concurrent access doesn't cause RuntimeError."""
        import threading
        from nanobot.utils.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=1000, window_seconds=60)
        errors = []
        completed = []

        def worker(worker_id: int):
            try:
                for i in range(100):
                    limiter.is_allowed(f"worker{worker_id}_user{i}")
                completed.append(worker_id)
            except RuntimeError as e:
                errors.append(e)

        # Create 20 threads accessing the limiter concurrently
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All workers should complete without RuntimeError
        assert len(completed) == 20, f"Some workers failed: {errors}"
        assert len(errors) == 0, f"Concurrent access caused errors: {errors}"

    def test_concurrent_cleanup_during_access(self):
        """Test that cleanup during concurrent access is safe."""
        import threading
        import time
        from nanobot.utils.rate_limit import RateLimiter

        # Use short max_age to trigger frequent cleanup
        limiter = RateLimiter(
            max_requests=10,
            window_seconds=60,
            max_age_seconds=0,  # Immediate cleanup
            max_entries=50,     # Low limit to trigger LRU eviction
        )
        errors = []

        def worker():
            try:
                for i in range(100):
                    limiter.is_allowed(f"user{i}")
            except RuntimeError as e:
                errors.append(e)

        # Create many threads to trigger cleanup concurrently
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent cleanup caused errors: {errors}"
```

**Steps:**
1. Add the test class to `tests/test_vision.py`
2. Run: `pytest tests/test_vision.py::TestRateLimiterConcurrency -v`
3. Verify tests pass (they should with current threading.Lock implementation)

---

## Phase 3: Code Quality Improvements (Priority 4)

### Fix #4: Fix Inconsistent uuid Import

**File:** `nanobot/channels/telegram.py`

**Check:** Verify that `uuid` is imported at the top (line 5) and remove any inline imports.

**Current (line 5):**
```python
import uuid
```

**Check line 290 area:** If there's an inline `import uuid`, remove it.

**Steps:**
1. Search for `import uuid` in the file
2. Ensure it's only at the top
3. Run tests: `pytest tests/ -k telegram -v`

---

### Fix #5: Document Magic Number

**File:** `nanobot/agent/video.py:104`

**Current:**
```python
DEFAULT_PROCESS_WAIT_TIMEOUT = 5.0
```

**Fix:**
```python
# Time to wait for process to terminate after SIGKILL
# - Most processes terminate within 100ms after kill()
# - 5 seconds handles edge cases (stuck in uninterruptible syscall, NFS, etc.)
# - This is a generous timeout to avoid hanging shutdown
DEFAULT_PROCESS_WAIT_TIMEOUT = 5.0
```

---

### Fix #6: Document Rate Limiter Scoping

**File:** `nanobot/channels/telegram.py:137-139`

**Current:**
```python
self._tts_rate_limiter = tts_rate_limiter()
self._transcription_rate_limiter = transcription_rate_limiter()
self._video_rate_limiter = video_rate_limiter()
```

**Fix (add comment before):**
```python
# Rate limiters are created per-channel-instance (not global singletons).
# Each TelegramChannel has independent rate limit quotas.
# If you want global rate limiting across all channels, inject shared instances.
self._tts_rate_limiter = tts_rate_limiter()
self._transcription_rate_limiter = transcription_rate_limiter()
self._video_rate_limiter = video_rate_limiter()
```

---

### Fix #7: Create Backwards Compatibility Removal Plan

**File:** New file `docs/TODO_v2.md` (or add to `CLAUDE.md`)

**Content:**
```markdown
# v2.0 Breaking Changes and Cleanup

## Deprecated Rate Limiter Classes

The following classes are deprecated and will be removed in v2.0:
- `TTSRateLimiter` → Use `tts_rate_limiter()` function instead
- `TranscriptionRateLimiter` → Use `transcription_rate_limiter()` instead
- `VideoRateLimiter` → Use `video_rate_limiter()` instead
- `VisionRateLimiter` → Use `vision_rate_limiter()` instead

### Migration Guide

**Before (v1.x):**
```python
from nanobot.utils import TTSRateLimiter

limiter = TTSRateLimiter()
```

**After (v2.0):**
```python
from nanobot.utils import tts_rate_limiter

limiter = tts_rate_limiter()
```

### Rationale

Factory functions provide:
1. Cleaner API (no need to instantiate classes)
2. Easier customization (can add parameters later)
3. Consistent with Python standard library patterns
4. Reduced code complexity (~40 lines removed)

---

## Other Potential v2.0 Changes

### Remove Deprecated Channel Methods
(Track as they are identified)

### Configuration Schema Changes
(Track as they are identified)
```

---

## Implementation Checklist

### Phase 1: Critical Fixes
- [ ] Fix #1: TTSProvider async I/O
  - [ ] Modify `nanobot/providers/tts.py`
  - [ ] Run `pytest tests/test_tts.py -v`
  - [ ] Verify all tests pass
- [ ] Fix #2: ProcessRegistry initialization
  - [ ] Modify `nanobot/agent/video.py`
  - [ ] Run `pytest tests/test_vision.py -v`
  - [ ] Verify all tests pass

### Phase 2: Testing
- [ ] Fix #3: Add concurrency tests
  - [ ] Add test class to `tests/test_vision.py`
  - [ ] Run new tests in isolation
  - [ ] Verify they pass

### Phase 3: Code Quality
- [ ] Fix #4: Fix uuid import
  - [ ] Check and fix `nanobot/channels/telegram.py`
  - [ ] Run tests
- [ ] Fix #5: Document magic number
  - [ ] Add comment to `nanobot/agent/video.py`
- [ ] Fix #6: Document rate limiter scoping
  - [ ] Add comment to `nanobot/channels/telegram.py`
- [ ] Fix #7: Create v2.0 plan
  - [ ] Create `docs/TODO_v2.md`

### Final Verification
- [ ] Run all tests: `pytest`
- [ ] Run linter: `ruff check nanobot/`
- [ ] Verify line count: `bash core_agent_lines.sh`
- [ ] Update CLAUDE.md if needed

---

## Testing Strategy

### For Fix #1 (TTSProvider):
```bash
# Run TTS tests
pytest tests/test_tts.py -v

# Run all tests to ensure no regression
pytest
```

### For Fix #2 (ProcessRegistry):
```bash
# Run video processing tests
pytest tests/test_vision.py::TestVideoProcessorSecurity -v

# Run all tests
pytest
```

### For Fix #3 (Concurrency Tests):
```bash
# Run new concurrency tests
pytest tests/test_vision.py::TestRateLimiterConcurrency -v

# Run with verbose output to see threading behavior
pytest tests/test_vision.py::TestRateLimiterConcurrency -v -s
```

### For All Fixes:
```bash
# Full test suite
pytest

# With coverage
pytest --cov=nanobot

# Linter
ruff check nanobot/
```

---

## Rollback Plan

If any fix causes issues:

1. **Revert individual commit:**
   ```bash
   git revert <commit-hash>
   ```

2. **Revert entire fix batch:**
   ```bash
   git reset --hard HEAD~1  # If commits are sequential
   ```

3. **Branch strategy:** Consider creating a `fix/remaining-issues` branch from `feature/multimodal-support` to isolate fixes.

---

## Expected Outcomes

After completing this plan:

1. **No blocking I/O in async contexts** - Better event loop responsiveness
2. **Thread-safe initialization** - No race conditions on startup
3. **Verified thread safety** - Tests confirm concurrent access works
4. **Better documentation** - Future maintainers understand design decisions
5. **Cleaner code** - Import inconsistencies and magic numbers addressed

**Line Count Impact:** +~50 lines (tests and documentation)

**Security Impact:** Low (no critical security issues)

**Performance Impact:** Low-positive (non-blocking I/O helps responsiveness)

---

## References

- Original code review: See `CODE_REVIEW_ISSUES.md`
- Related commits: `0ba1ea7`, `78369ee`, `72e0a75`
- Test files: `tests/test_vision.py`, `tests/test_tts.py`
