import { Link, useLocation } from 'react-router-dom';
import { AppProvider, useApp } from '@/components/context/AppContext';
import { 
  MessageCircle, 
  Users, 
  QrCode, 
  Settings, 
  Cat,
  LogOut
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Inner layout component that uses the context
function MeshCatLayout({ children }) {
  const { user, theme, connectionStatus } = useApp();
  const location = useLocation();
  const isDarkMode = theme === 'dark';

  return (
    <div className={cn(
      "min-h-screen transition-colors duration-300 font-sans flex flex-col md:flex-row",
      isDarkMode ? "bg-slate-950 text-slate-100 scheme-dark" : "bg-[#F5F5FA] text-slate-900 scheme-light"
    )}>
      {/* Desktop Sidebar - Only visible when logged in */}
      {user && (
        <aside className="hidden md:flex flex-col w-80 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 h-screen sticky top-0">
          <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3">
             <div className="w-10 h-10 bg-gradient-to-tr from-violet-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
               <Cat className="text-white w-6 h-6" />
             </div>
             <div>
               <h1 className="font-bold text-xl tracking-tight">MeshCat</h1>
               <StatusBadge status={connectionStatus} />
             </div>
          </div>
          
          <nav className="flex-1 px-4 py-6 space-y-2">
            <NavItem to="/chatlist" icon={MessageCircle} label="Chats" active={location.pathname === '/' || location.pathname === '/chatlist' || location.pathname.startsWith('/chat')}/>
            <NavItem to="/contacts" icon={Users} label="Contacts" active={location.pathname === '/contacts'} />
            <NavItem to="/profile" icon={QrCode} label="Profile" active={location.pathname === '/profile'} />
            <NavItem to="/settings" icon={Settings} label="Settings" active={location.pathname === '/settings'} />
          </nav>

          <div className="p-4 border-t border-slate-100 dark:border-slate-800">
            <Link to="/profile" className="flex items-center gap-3 px-2 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
               <img src={user.avatarUrl} className="w-10 h-10 rounded-full bg-white object-cover" alt="Me" />
               <div className="flex-1 min-w-0">
                 <p className="font-medium text-sm truncate">{user.displayName}</p>
                 <p className="text-xs text-slate-500 truncate">@{user.username}</p>
               </div>
            </Link>
          </div>
        </aside>
      )}

      {/* Mobile Header - Only visible when logged in */}
      {user && (
        <header className="md:hidden h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 sticky top-0 z-50">
          <div className="flex items-center gap-2">
             <div className="w-8 h-8 bg-gradient-to-tr from-violet-600 to-indigo-600 rounded-lg flex items-center justify-center">
               <Cat className="text-white w-5 h-5" />
             </div>
             <span className="font-bold text-lg">MeshCat</span>
          </div>
          <StatusBadge status={connectionStatus} minimal />
        </header>
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-[calc(100vh-4rem)] md:h-screen overflow-hidden relative">
        {!user && !location.pathname.includes('onboarding') && !location.pathname.includes('sign-in') ? (
           <div className="flex-1 flex items-center justify-center p-6 text-center">
             <div className="max-w-md space-y-4 w-full">
               <div className="w-20 h-20 bg-gradient-to-tr from-violet-600 to-indigo-600 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-xl shadow-indigo-500/20">
                 <Cat className="w-10 h-10 text-white" />
               </div>
               <h2 className="text-3xl font-bold text-slate-900 dark:text-white">MeshCat</h2>
               <p className="text-slate-500 text-lg">Decentralized Mesh Messaging</p>
               
               <div className="pt-8 space-y-3">
                 <Link to="/onboarding" className="flex items-center justify-center w-full px-6 py-3.5 rounded-xl bg-violet-600 text-white font-semibold hover:bg-violet-700 transition-colors shadow-lg shadow-violet-500/20">
                   Create New Identity
                 </Link>
                 <Link to="/sign-in" className="flex items-center justify-center w-full px-6 py-3.5 rounded-xl bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                   Login with Existing ID
                 </Link>
               </div>
             </div>
           </div>
        ) : children}
      </main>

      {/* Mobile Bottom Tab Bar - Only visible when logged in */}
      {user && (
        <nav className="md:hidden h-16 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 flex items-center justify-around px-2 pb-safe sticky bottom-0 z-50">
          <TabItem to="/chatlist" icon={MessageCircle} label="Chats" active={location.pathname === '/' || location.pathname === '/chatlist' || location.pathname.startsWith('/chat')} />
          <TabItem to="/contacts" icon={Users} label="People" active={location.pathname === '/contacts'} />
          <TabItem to="/profile" icon={QrCode} label="Profile" active={location.pathname === '/profile'} />
          <TabItem to="/settings" icon={Settings} label="Settings" active={location.pathname === '/settings'} />
        </nav>
      )}
    </div>
  );
}

function StatusBadge({ status, minimal = false }) {
  const config = {
    connected: { color: 'bg-green-500', text: 'Online' },
    connecting: { color: 'bg-yellow-500', text: 'Connecting...' },
    error: { color: 'bg-red-500', text: 'Offline' }
  }[status] || { color: 'bg-slate-400', text: 'Unknown' };

  if (minimal) {
    return <div className={`w-2.5 h-2.5 rounded-full ${config.color}`} title={config.text} />;
  }

  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${config.color}`} />
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{config.text}</span>
    </div>
  );
}

function NavItem({ to, icon: Icon, label, active }) {
  return (
    <Link to={to} className={cn(
      "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all font-medium",
      active 
        ? "bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300" 
        : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50"
    )}>
      <Icon className={cn("w-5 h-5", active ? "text-violet-600 dark:text-violet-400" : "text-slate-500")} />
      <span>{label}</span>
    </Link>
  );
}

function TabItem({ to, icon: Icon, label, active }) {
  return (
    <Link to={to} className={cn(
      "flex flex-col items-center justify-center gap-1 p-1 flex-1 h-full transition-colors",
      active 
        ? "text-violet-600 dark:text-violet-400" 
        : "text-slate-400 dark:text-slate-500"
    )}>
      <Icon className={cn("w-6 h-6", active && "fill-current/10")} />
      <span className="text-[10px] font-medium">{label}</span>
    </Link>
  );
}

// Export the wrapper
export default function Layout({ children }) {
  return (
    <AppProvider>
      <MeshCatLayout>{children}</MeshCatLayout>
    </AppProvider>
  );
}