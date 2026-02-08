# Backend API Patterns

FastAPI layered architecture with typing and dependency injection.

## When to Use
- Creating REST endpoints
- Modifying existing APIs
- Adding database operations
- Implementing CRUD operations

## Checklist
- [ ] Endpoint → Service → Model separation
- [ ] Define `response_model` for validation
- [ ] Use dependency injection for db and auth
- [ ] Request validation (Pydantic schemas)
- [ ] Type hint return values
- [ ] Async where I/O-bound

## Examples

### Basic CRUD Endpoint
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/items", tags=["items"])

@router.get("", response_model=list[ItemResponse])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db)
) -> list[ItemResponse]:
    result = await db.execute(select(Item).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(data: ItemCreate, db: AsyncSession = Depends(get_db)):
    item = Item(**data.dict())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
```

## Avoid
- ❌ Direct DB access in routes → ✅ Use service layer
- ❌ Missing response models → ✅ Define `response_model`
- ❌ Sync operations for I/O → ✅ Use async/await
- ❌ No dependency injection → ✅ Use `Depends()`

### Service Layer Pattern
```python
class ItemService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def create(self, data: ItemCreate) -> Item:
        item = Item(**data.dict())
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

# Endpoint uses service
@router.post("", response_model=ItemResponse)
async def create_item(data: ItemCreate, service: ItemService = Depends()):
    return await service.create(data)
```

### Pydantic Schema
```python
from pydantic import BaseModel, Field
from datetime import datetime

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
```

## Related Skills
- `debugging.md` - Troubleshooting endpoints
- `frontend-react.md` - API integration patterns
