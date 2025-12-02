import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useApp } from '@/components/context/AppContext';
import { apiClient } from '@/components/services/apiClient';
import { Cat, ArrowRight, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';

type User = {
  id: string;
  username: string;
  displayName: string;
  avatarUrl: string;
};

export default function Onboarding() {
  const { user, setUser } = useApp();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    if (user) {
      navigate('/chatlist');
    }
  }, [user, navigate]);
  const [formData, setFormData] = useState({
    username: '',
    displayName: '',
    password: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.username || !formData.displayName || !formData.password) return;

    setLoading(true);
    try {
      // Create profile with random avatar
      const profile = await apiClient.createProfile({
        ...formData,
        avatarUrl: `https://api.dicebear.com/7.x/avataaars/svg?seed=${formData.username}`
      });
      setUser(profile as User);
      navigate('/chatlist');
    } catch (error) {
      toast.error(error.message || "Failed to create profile");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-full flex flex-col items-center justify-center p-6 bg-white dark:bg-slate-950 animate-in fade-in duration-500">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-2">
          <div className="w-20 h-20 bg-gradient-to-tr from-violet-600 to-indigo-600 rounded-3xl flex items-center justify-center mx-auto shadow-xl shadow-indigo-500/20 mb-6">
            <Cat className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            Create Identity
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            Join the decentralized mesh network.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 bg-slate-50 dark:bg-slate-900/50 p-8 rounded-3xl border border-slate-100 dark:border-slate-800">
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <div className="relative">
              <span className="absolute left-3 top-2.5 text-slate-400">@</span>
              <Input
                id="username"
                placeholder="meshcat.alice"
                className="pl-8 bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800"
                value={formData.username}
                onChange={e => setFormData({ ...formData, username: e.target.value })}
                required
              />
            </div>
            <p className="text-xs text-slate-500">Unique identifier on the network.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="displayName">Display Name</Label>
            <Input
              id="displayName"
              placeholder="Alice Wonderland"
              className="bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800"
              value={formData.displayName}
              onChange={e => setFormData({ ...formData, displayName: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              className="bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800"
              value={formData.password}
              onChange={e => setFormData({ ...formData, password: e.target.value })}
              required
            />
          </div>

          <Button 
            type="submit" 
            className="w-full h-12 bg-violet-600 hover:bg-violet-700 text-white rounded-xl"
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <span className="flex items-center gap-2">
                Create Profile <ArrowRight className="w-4 h-4" />
              </span>
            )}
          </Button>
        </form>

        <div className="text-center">
          <Link to="/sign-in" className="text-sm text-violet-600 hover:text-violet-700 font-medium">
            Already have an identity? Login
          </Link>
        </div>
      </div>
    </div>
  );
}