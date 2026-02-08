import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', icon: '🔍', label: 'Search' },
  { path: '/activity', icon: '📥', label: 'Activity' },
  { path: '/history', icon: '📜', label: 'History' },
  { path: '/stats', icon: '📊', label: 'Stats' },
  { path: '/settings', icon: '⚙️', label: 'Settings' },
];

export function Sidebar() {
  return (
    <aside className="w-56 bg-arr-sidebar h-screen fixed left-0 top-0 border-r border-arr-border">
      {/* Logo */}
      <div className="p-4 border-b border-arr-border">
        <h1 className="text-xl font-bold text-arr-accent">XDCCarr</h1>
        <p className="text-xs text-arr-text-muted">XDCC Indexer for *arr</p>
      </div>
      
      {/* Navigation */}
      <nav className="p-2">
        {navItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive 
                  ? 'bg-arr-accent text-white' 
                  : 'text-arr-text hover:bg-arr-bg-alt'
              }`
            }
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      
      {/* Status */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-arr-border">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-arr-success rounded-full"></span>
          <span className="text-sm text-arr-text-muted">Connected</span>
        </div>
      </div>
    </aside>
  );
}
