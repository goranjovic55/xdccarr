# Frontend React & UI Consistency

## When to Use
- Building React components
- Implementing UI designs
- Standardizing component patterns
- Creating reusable UI elements
- Maintaining design system consistency

## Avoid
- ❌ Inline styles → ✅ CSS modules or styled-components
- ❌ Duplicate components → ✅ Reusable abstractions
- ❌ Inconsistent styling → ✅ Follow design system
- ❌ Prop drilling → ✅ Context or state management

## Overview

Build consistent, reusable React components following established design patterns. Use TypeScript for type safety, maintain component library standards, and ensure UI consistency across the application.

---

## Component Structure

**Standard Pattern:**
```tsx
interface ComponentProps {
  title: string;
  onAction: () => void;
  variant?: 'primary' | 'secondary';
}

export const Component: React.FC<ComponentProps> = ({ 
  title, 
  onAction, 
  variant = 'primary' 
}) => {
  return (
    <div className={`component component-${variant}`}>
      <h2>{title}</h2>
      <button onClick={onAction}>Action</button>
    </div>
  );
};
```

---

## State Management

**Zustand (Preferred):**
```tsx
// store/useAppStore.ts
import { create } from 'zustand';

interface AppState {
  items: Item[];
  addItem: (item: Item) => void;
}

export const useAppStore = create<AppState>((set) => ({
  items: [],
  addItem: (item) => set((state) => ({ 
    items: [...state.items, item] 
  })),
}));

// Component usage
const { items, addItem } = useAppStore();
```

**React Context (for UI state):**
```tsx
const ThemeContext = React.createContext<Theme>(defaultTheme);

export const ThemeProvider: React.FC = ({ children }) => {
  const [theme, setTheme] = useState(defaultTheme);
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

---

## Design System Integration

**Using Design Tokens:**
```tsx
// Follow established color/spacing variables
const Button = styled.button`
  background: var(--color-primary);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  color: var(--color-text-inverse);
`;
```

**Component Variants:**
```tsx
const variants = {
  primary: 'bg-red-600 text-white',
  secondary: 'bg-gray-600 text-white',
  outline: 'border-2 border-red-600 text-red-600',
};

<Button className={variants[variant]} />
```

---

## Common Patterns

### Reusable Card Component
```tsx
interface CardProps {
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ title, children, actions }) => (
  <div className="card">
    <div className="card-header">
      <h3>{title}</h3>
      {actions && <div className="card-actions">{actions}</div>}
    </div>
    <div className="card-body">{children}</div>
  </div>
);
```

### Modal Pattern
```tsx
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button onClick={onClose}>×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
};
```

### Form Handling
```tsx
const [formData, setFormData] = useState({ name: '', email: '' });

const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
};

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  await api.submit(formData);
};
```

---

## TypeScript Best Practices

**Props with Children:**
```tsx
interface Props {
  title: string;
  children: React.ReactNode;
}
```

**Event Handlers:**
```tsx
onClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
```

**Component Types:**
```tsx
const Component: React.FC<Props> = () => { }; // Functional component
const Component = ({ prop }: Props) => { };   // Alternative
```

---

## Performance

**Memoization:**
```tsx
const MemoizedComponent = React.memo(ExpensiveComponent);

const memoizedValue = useMemo(() => computeExpensive(a, b), [a, b]);

const memoizedCallback = useCallback(() => {
  doSomething(a, b);
}, [a, b]);
```

**Lazy Loading:**
```tsx
const LazyComponent = React.lazy(() => import('./Component'));

<Suspense fallback={<Loading />}>
  <LazyComponent />
</Suspense>
```

---

## Styling Approaches

**CSS Modules:**
```tsx
import styles from './Component.module.css';
<div className={styles.container} />
```

**Tailwind CSS:**
```tsx
<div className="flex items-center gap-4 p-4 bg-gray-900 rounded-lg" />
```

**Styled Components:**
```tsx
const Container = styled.div`
  display: flex;
  padding: 1rem;
`;
```

---

## Testing

**Component Test:**
```tsx
import { render, screen } from '@testing-library/react';

test('renders component', () => {
  render(<Component title="Test" />);
  expect(screen.getByText('Test')).toBeInTheDocument();
});
```

---

## Checklist

Component creation:
- [ ] TypeScript interfaces defined
- [ ] Props validated
- [ ] Consistent styling applied
- [ ] Reusable and composable
- [ ] Accessibility attributes (aria-*, role)
- [ ] Tests written

## Related Skills
- `backend-api.md` - API integration
- `debugging.md` - Component debugging
- `documentation.md` - Component documentation

## Related Docs
- [UI/UX Spec](../../docs/design/UI_UX_SPEC.md)
- [Unified Style Guide](../../docs/design/UNIFIED_STYLE_GUIDE.md)
