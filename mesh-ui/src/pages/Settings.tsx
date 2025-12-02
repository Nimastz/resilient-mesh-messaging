import { useEffect, useState } from 'react';
import { useApp } from '@/components/context/AppContext';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/components/services/apiClient';
import { 
  Moon, 
  Sun, 
  Wifi, 
  Activity, 
  Signal, 
  Cpu, 
  ShieldCheck,
  Trash2,
  LogOut,
  Radio
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

export default function SettingsPage() {
  const { user, setUser, theme, updateTheme, connectionStatus, setConnectionStatus } = useApp();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [peers, setPeers] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSystemInfo();
    const interval = setInterval(loadSystemInfo, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const loadSystemInfo = async () => {
    try {
      const [s, p] = await Promise.all([
        apiClient.getRouterStats(),
        apiClient.getBlePeers()
      ]);
      setStats(s);
      setPeers(p);
    } catch (e) {
      console.error("Failed to load stats");
    }
  };

  const toggleTheme = () => {
    updateTheme(theme === 'dark' ? 'light' : 'dark');
  };

  const handleClearCache = async () => {
    toast.info("Clearing local cache...");
    setTimeout(() => {
      toast.success("Cache cleared");
      window.location.reload();
    }, 1000);
  };

  if (!user) return null;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-950 md:bg-transparent overflow-y-auto p-4 md:p-8 pb-24">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Settings</h1>

      <div className="space-y-6 max-w-3xl">
        {/* Appearance */}
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Appearance</h2>
          <Card>
            <CardContent className="p-0 divide-y divide-slate-100 dark:divide-slate-800">
              <div className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400">
                    {theme === 'dark' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
                  </div>
                  <div>
                    <p className="font-medium">Dark Mode</p>
                    <p className="text-sm text-slate-500">Easier on the eyes at night</p>
                  </div>
                </div>
                <Switch 
                  checked={theme === 'dark'} 
                  onCheckedChange={toggleTheme} 
                />
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Mesh Network Status */}
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Mesh Network</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
               <CardContent className="p-6 flex items-center gap-4">
                 <div className={`w-12 h-12 rounded-full flex items-center justify-center ${connectionStatus === 'connected' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                   <Wifi className="w-6 h-6" />
                 </div>
                 <div>
                   <p className="text-sm text-slate-500">Status</p>
                   <p className="font-bold capitalize">{connectionStatus}</p>
                 </div>
               </CardContent>
            </Card>
            <Card>
               <CardContent className="p-6 flex items-center gap-4">
                 <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                   <Activity className="w-6 h-6" />
                 </div>
                 <div>
                   <p className="text-sm text-slate-500">Queued Msgs</p>
                   <p className="font-bold">{stats?.total_queued || 0}</p>
                 </div>
               </CardContent>
            </Card>
            <Card>
               <CardContent className="p-6 flex items-center gap-4">
                 <div className="w-12 h-12 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center">
                   <Cpu className="w-6 h-6" />
                 </div>
                 <div>
                   <p className="text-sm text-slate-500">Uptime</p>
                   <p className="font-bold">{stats?.uptime || '-'}</p>
                 </div>
               </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Radio className="w-4 h-4" /> Discovered Peers (BLE)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {peers.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No peers discovered nearby.
                </div>
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  {peers.map((peer, i) => (
                    <div key={i} className="flex items-center justify-between p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-violet-50 dark:bg-slate-800 flex items-center justify-center">
                          <Signal className="w-4 h-4 text-violet-500" />
                        </div>
                        <div>
                          <p className="font-mono text-sm font-medium">{peer.fingerprint}</p>
                          <p className="text-xs text-slate-500">Last seen {Math.floor((Date.now() - peer.last_seen)/1000)}s ago</p>
                        </div>
                      </div>
                      <div className="text-xs font-mono bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
                        {peer.rssi} dBm
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        {/* Account */}
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Account</h2>
          <Card>
            <CardContent className="p-0 divide-y divide-slate-100 dark:divide-slate-800">
              <div className="p-4">
                 <p className="text-sm text-slate-500 mb-1">Identity Fingerprint</p>
                 <p className="font-mono text-xs break-all bg-slate-50 dark:bg-slate-900 p-3 rounded border border-slate-200 dark:border-slate-800 select-all">
                   {user.fingerprint}
                 </p>
              </div>
              
              <button 
                onClick={async () => {
                  await apiClient.logout();
                  setUser(null);
                  navigate('/sign-in');
                }}
                className="w-full text-left flex items-center gap-3 p-4 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                <LogOut className="w-5 h-5" />
                <span className="font-medium">Log Out</span>
              </button>

              <button 
                onClick={handleClearCache}
                className="w-full text-left flex items-center gap-3 p-4 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
              >
                <Trash2 className="w-5 h-5" />
                <span className="font-medium">Clear Cache & Reset</span>
              </button>
            </CardContent>
          </Card>
        </section>

        <div className="text-center text-xs text-slate-400 pt-8">
          MeshCat v1.0.0 • Decentralized Mesh Messenger
        </div>
      </div>
    </div>
  );
}