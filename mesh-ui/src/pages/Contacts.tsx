import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/components/services/apiClient';
import { useApp } from '@/components/context/AppContext';
import { Search, UserPlus, QrCode, MessageSquare, Trash2, Shield, Ghost } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';

export default function Contacts() {
  const { user } = useApp();
  const navigate = useNavigate();
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [addUsername, setAddUsername] = useState('');
  const [adding, setAdding] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);

  useEffect(() => {
    if (user) loadContacts();
  }, [user]);

  const loadContacts = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getContacts();
      setContacts(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAddByUsername = async () => {
    if (!addUsername) return;
    setAdding(true);
    try {
      // In a real app, we'd search for the user first. 
      // Here we simulate adding them by username if they don't exist in contacts
      await apiClient.addContact({
         username: addUsername,
         displayName: addUsername,
         fingerprint: `MESH-${Math.random().toString(36).substring(2,6).toUpperCase()}` // Simulated fingerprint
      });
      toast.success('Contact added successfully');
      setAddUsername('');
      setShowAddDialog(false);
      loadContacts();
    } catch (e) {
      toast.error(e.message || "Failed to add contact");
    } finally {
      setAdding(false);
    }
  };

  const startChat = async (contact) => {
    try {
      const conv = await apiClient.getOrCreateConversation(contact.id);
      navigate(`/chat?id=${conv.id}`);
    } catch (e) {
      toast.error("Failed to start chat");
    }
  };

  const handleDeleteContact = async (e, contactId) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this contact?")) return;
    try {
      await apiClient.deleteContact(contactId);
      setContacts(prev => prev.filter(c => c.id !== contactId));
      toast.success("Contact deleted");
    } catch (error) {
      toast.error("Failed to delete contact");
    }
  };

  const filtered = contacts.filter(c => 
    c.displayName?.toLowerCase().includes(search.toLowerCase()) || 
    c.username?.toLowerCase().includes(search.toLowerCase())
  );

  if (!user) return null;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-950 md:bg-transparent">
      <div className="p-4 md:p-6 space-y-4 border-b border-slate-100 dark:border-slate-800 md:border-none sticky top-0 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md md:bg-transparent z-10">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Contacts</h1>
          <div className="flex gap-2">
            <Button 
              variant="outline"
              size="icon" 
              className="rounded-full"
              onClick={() => navigate('/profile')}
            >
              <QrCode className="w-4 h-4" />
            </Button>
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
              <DialogTrigger asChild>
                <Button className="rounded-full bg-violet-600 hover:bg-violet-700 text-white">
                  <UserPlus className="w-4 h-4 md:mr-2" />
                  <span className="hidden md:inline">Add Contact</span>
                </Button>
              </DialogTrigger>
              
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add by Username</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label>Username</Label>
                    <Input 
                      placeholder="meshcat.username"
                      value={addUsername}
                      onChange={e => setAddUsername(e.target.value)}
                    />
                  </div>
                  <Button onClick={handleAddByUsername} disabled={adding} className="w-full">
                    {adding ? 'Adding...' : 'Add Contact'}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
          <Input 
            placeholder="Search contacts..." 
            className="pl-9 bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 rounded-xl h-10"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 md:px-6 pb-20 md:pb-6 space-y-2">
        {loading ? (
           <div className="flex justify-center p-10"><span className="animate-pulse text-slate-400">Loading contacts...</span></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center p-6">
            <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <Ghost className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-medium">No contacts found</h3>
            <p className="text-slate-500 text-sm mt-1">Try adding someone by username or QR code.</p>
          </div>
        ) : (
          filtered.map(contact => (
            <div key={contact.id} className="flex items-center gap-3 p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm">
              <img 
                src={contact.avatarUrl} 
                alt={contact.username} 
                className="w-12 h-12 rounded-full bg-slate-200 object-cover" 
              />
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                  {contact.displayName}
                </h3>
                <p className="text-xs text-slate-500 font-mono truncate">
                  @{contact.username} • {contact.fingerprint?.substring(0, 8)}...
                </p>
              </div>
              <div className="flex items-center gap-1">
                <Button 
                  size="icon" 
                  variant="ghost"
                  className="text-violet-600 hover:text-violet-700 hover:bg-violet-50 dark:hover:bg-violet-900/20"
                  onClick={() => startChat(contact)}
                >
                  <MessageSquare className="w-5 h-5" />
                </Button>
                <Button 
                  size="icon" 
                  variant="ghost"
                  className="text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                  onClick={(e) => handleDeleteContact(e, contact.id)}
                >
                  <Trash2 className="w-5 h-5" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}