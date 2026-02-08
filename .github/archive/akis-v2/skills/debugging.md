# Debugging

Systematic troubleshooting for build, runtime, and infrastructure errors.

## When to Use
- Build/compile errors
- Runtime exceptions
- Container/Docker issues
- API integration failures
- Type errors

## Checklist
- [ ] Read complete error message
- [ ] Check recent changes (`git diff`)
- [ ] Isolate failing component
- [ ] Reproduce in minimal case
- [ ] Fix and verify related areas

## Examples

### Build Errors

**TypeScript Module Not Found:**
```bash
# Check imports
grep -r "import.*X" src/

# Install if missing
npm install X

# Fix path
import { X } from './components/X'  # Relative path
```

**Python Import Error:**
```bash
# Check if installed
pip list | grep package-name

# Install if missing
pip install package-name

# Fix relative import
from .module import X  # Not: from module import X
```

### Runtime Errors

**Backend 500 Error:**
```bash
# Check logs
docker compose logs backend | tail -50

# Check database
docker compose exec backend python -c "from app.core.database import test_connection; test_connection()"

# Enable debug mode
LOG_LEVEL=DEBUG docker compose up backend
```

**Frontend TypeError:**
```typescript
// Add null check
const value = data?.property ?? 'default';

// Type guard
if (typeof value === 'string') {
  // Safe to use as string
}
```

### Docker Issues

**Container Won't Start:**
```bash
# Check logs
docker compose logs service-name

# Inspect container
docker compose ps
docker inspect container-id

# Rebuild
docker compose build --no-cache service-name
docker compose up -d service-name
```

**Port Already in Use:**
```bash
# Find process
lsof -i :8000
kill <PID>

# Or change port in docker-compose.yml
```

### Type Errors

**TypeScript:**
```typescript
// Fix missing property
interface User {
  id: number;
  name: string;
  email?: string;  // Optional with ?
}

// Type assertion when certain
const user = data as User;

// Type narrowing
if ('property' in object) {
  // Safe to access object.property
}
```

**Python:**
```python
# Type hints
def process(data: dict[str, Any]) -> list[str]:
    return list(data.keys())

# Optional types
from typing import Optional
def get_user(id: int) -> Optional[User]:
    return user or None
```

### Error Handling

**Try-Catch Pattern:**
```typescript
try {
  await riskyOperation();
} catch (error) {
  console.error('Operation failed:', error);
  // Handle gracefully
  return defaultValue;
}
```

**Python Exception Handling:**
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    result = default_value
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

## Quick Fixes

| Error | Solution |
|-------|----------|
| Module not found | Install package or fix import path |
| Type error | Add type hint or assertion |
| Port in use | Kill process or change port |
| Container fails | Check logs, rebuild with `--no-cache` |
| API 500 | Check backend logs, verify database |
| Null/undefined | Add null checks (`?.` or `??`) |

## Related
- `backend-api.md` - Backend patterns
- `frontend-react.md` - Frontend patterns
