# UI Consistency

Maintain consistent React component design and cyberpunk theme.

## When to Use
- Creating new UI components
- Styling pages or features
- Implementing cyberpunk theme
- Building responsive layouts

## Checklist
- [ ] Use CyberUI components (CyberCard, CyberButton, CyberInput)
- [ ] Apply cyberpunk color palette (neon colors on dark bg)
- [ ] Consistent spacing (p-4, gap-4, space-y-2)
- [ ] Responsive grid layouts (grid-cols-1 md:grid-cols-2 lg:grid-cols-3)
- [ ] Status indicators (green=success, red=error, yellow=warning)
- [ ] Glow effects on interactive elements

## Examples

### CyberCard Component
```tsx
<div className="bg-gray-900 border border-red-500 rounded-lg p-6 shadow-lg hover:shadow-red-500/50">
  <h3 className="text-xl font-bold text-red-500 mb-2 uppercase">
    Card Title
  </h3>
  <p className="text-gray-400">Card content</p>
</div>
```

### Status Badge
```tsx
const StatusBadge = ({ status }: { status: string }) => {
  const colors = {
    online: 'bg-green-500/20 text-green-400 border-green-500',
    offline: 'bg-gray-500/20 text-gray-400 border-gray-500',
    error: 'bg-red-500/20 text-red-400 border-red-500'
  };
  
  return (
    <span className={`px-2 py-1 rounded border text-xs ${colors[status]}`}>
      {status.toUpperCase()}
    </span>
  );
};
```

### Responsive Grid
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(item => (
    <CyberCard key={item.id}>
      <h3>{item.name}</h3>
      <StatusBadge status={item.status} />
    </CyberCard>
  ))}
</div>
```

### Interactive Button
```tsx
<button className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 
  transition-all duration-200 shadow-lg hover:shadow-red-500/50 
  border border-red-400">
  ACTION
</button>
```

## Related
- `frontend-react.md` - React patterns
- `docs/design/UI_UX_SPEC.md` - Complete design system
