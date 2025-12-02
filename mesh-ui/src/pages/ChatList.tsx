import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/components/services/apiClient';
import { useApp } from '@/components/context/AppContext';
import { Search, Plus, Clock, Check, CheckCheck, AlertCircle, Trash2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { format } from 'date-fns';

export default function Chats() {
  const { user } = useApp();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (user) {
      loadConversations();
    }
  }, [user]);

  const loadConversations = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getConversations();
      setConversations(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteChat = async (e, id) => {
    e.preventDefault(); // Prevent navigation
    if (!confirm("Delete this conversation?")) return;
    try {
      await apiClient.deleteConversation(id);
      setConversations(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  const filtered = conversations.filter(c => 
    c.contact?.displayName.toLowerCase().includes(search.toLowerCase()) || 
    c.contact?.username.toLowerCase().includes(search.toLowerCase())
  ).sort((a, b) => {
    const timeA = new Date(a.lastMessageTime || 0).getTime();
    const timeB = new Date(b.lastMessageTime || 0).getTime();
    return timeB - timeA;
  });

  if (!user) return null;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-950 md:bg-transparent">
      <div className="p-4 md:p-6 space-y-4 border-b border-slate-100 dark:border-slate-800 md:border-none sticky top-0 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md md:bg-transparent z-10">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Chats</h1>

        </div>
        <div className="relative">
          <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
          <Input 
            placeholder="Search conversations..." 
            className="pl-9 bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 rounded-xl h-10"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 md:px-6 pb-20 md:pb-6 space-y-1">
        {loading ? (
          <div className="space-y-3 p-2">
             {[1,2,3].map(i => (
               <div key={i} className="flex gap-3 animate-pulse">
                 <div className="w-12 h-12 rounded-full bg-slate-200 dark:bg-slate-800" />
                 <div className="flex-1 space-y-2 py-1">
                   <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/3" />
                   <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-2/3" />
                 </div>
               </div>
             ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center p-6">
            <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <Plus className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-medium">No chats yet</h3>
            <p className="text-slate-500 text-sm mt-1 mb-4">Start a conversation with a contact.</p>
            <Button variant="outline" onClick={() => navigate('/contacts')}>Find People</Button>
          </div>
        ) : (
          filtered.map(conv => (
            <Link 
              key={conv.id} 
              to={`/chat?id=${conv.id}`}
              className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors group border-b border-slate-50 dark:border-slate-800/50 last:border-0"
            >
              <div className="inline-flex items-center justify-center rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none bg-violet-600 text-white hover:bg-violet-700 h-10 w-10 rounded-full bg-violet-100 text-violet-600 hover:bg-violet-200 dark:bg-violet-500/20 dark:text-violet-300 shrink-0 overflow-hidden">
                <img 
                  src={conv.contact?.avatarUrl} 
                  alt={conv.contact?.username} 
                  className="w-full h-full object-cover" 
                />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <div className="flex items-center gap-2">
                     <h3 className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                       {conv.contact?.displayName || 'Unknown'}
                     </h3>
                     <span className="text-xs text-slate-400">@{conv.contact?.username}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-500 dark:text-slate-400 truncate flex-1 pr-2">
                      {conv.lastMessageText || 'No messages'}
                    </p>
                    <div className="flex items-center gap-2">
                        {conv.lastMessageTime && (
                            <span className="text-xs text-slate-400 whitespace-nowrap">
                            {format(new Date(conv.lastMessageTime), 'h:mm a')}
                            </span>
                        )}
                        {conv.unreadCount > 0 && (
                            <div className="w-5 h-5 rounded-full bg-green-500 text-red-600 text-[10px] font-bold flex items-center justify-center shadow-sm">
                            {conv.unreadCount}
                            </div>
                        )}
                    </div>
                </div>
              </div>
              
              <button
                onClick={(e) => handleDeleteChat(e, conv.id)}
                className="opacity-0 group-hover:opacity-100 p-2 text-slate-400 hover:text-red-500 transition-all"
                title="Delete chat"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}