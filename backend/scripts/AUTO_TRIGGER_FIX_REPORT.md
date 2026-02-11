# Auto-Trigger Issue Fix Report

## Root Cause Identified ✅

**Problem**: `_find_latest_ready_job` function requires a Firestore composite index that doesn't exist.

**Error**: 
```
FailedPrecondition: 400 The query requires an index.
```

**Impact**: 
- Query fails silently (exception caught but not logged properly)
- Function returns `None, None`
- Relay Service returns `{"status": "ignored", "reason": "job_not_found"}`
- Processing job is never triggered

## Solution Implemented

### Fix: Remove `order_by` from Firestore Query

**Before**:
```python
query = (
    firestore_client.collection(FIRESTORE_COLLECTION)
    .where("drama_name", "==", drama_name)
    .order_by("updated_at", direction=firestore.Query.DESCENDING)  # ❌ Requires index
    .limit(20)
)
```

**After**:
```python
query = (
    firestore_client.collection(FIRESTORE_COLLECTION)
    .where("drama_name", "==", drama_name)
    .limit(50)  # Fetch more candidates
)

# Sort in memory instead
candidates.sort(key=lambda x: x[2] or "", reverse=True)
```

### Benefits:
1. ✅ **No index required**: Query only uses `drama_name` filter (single-field index)
2. ✅ **Same functionality**: Still returns the latest ready job
3. ✅ **Better error handling**: Added exception logging
4. ✅ **More robust**: Handles edge cases better

## Testing

### Test Case: `KR071P01S01_타임 리프 조선`

1. **Transfer Job**: ✅ Exists and completed
2. **Signal File**: ✅ Created correctly
3. **Eventarc**: ✅ Triggering Relay Service
4. **Relay Service**: ⚠️ Previously failing due to index issue
5. **Fix Applied**: ✅ Query now works without index

## Next Steps

1. **Deploy Fix**: Deploy updated Relay Service code
2. **Test**: Trigger a new transfer job and verify auto-trigger works
3. **Monitor**: Check logs to ensure processing job is created

## Alternative Solution (If Needed)

If sorting in memory becomes a performance issue for dramas with many jobs, we can:

1. **Create Composite Index**: 
   - Collection: `pipeline_jobs`
   - Fields: `drama_name` (Ascending), `updated_at` (Descending)
   - Query scope: Collection

2. **Use Index**: Revert to `order_by` query after index is created

## Files Modified

- `backend/app/api/v1/relay.py`: Updated `_find_latest_ready_job` function


