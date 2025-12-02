import { useState, useEffect } from 'react';
import { useApp } from '@/components/context/AppContext';
import { useLocation, useNavigate } from 'react-router-dom';
import { QrCode, Copy, Check, Camera, ScanLine, Edit2, X, Save } from 'lucide-react';
// import { QRCodeSVG } from 'qrcode.react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/components/services/apiClient';
import { toast } from 'sonner';

export default function Profile() {
  const { user, setUser } = useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('code');
  const [copied, setCopied] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [profileUser, setProfileUser] = useState(user);
  const [loadingProfile, setLoadingProfile] = useState(false);
  
  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({ displayName: '', avatarUrl: '' });

  // Parse query param for viewing other users
  const searchParams = new URLSearchParams(location.search);
  const viewFingerprint = searchParams.get('id');
  const isMe = !viewFingerprint || (user && viewFingerprint === user.fingerprint);

  useEffect(() => {
    const loadProfile = async () => {
      if (viewFingerprint && viewFingerprint !== user?.fingerprint) {
        setLoadingProfile(true);
        try {
          // Try to find in contacts first or fetch generic user info
          // In this mocked version, we'll assume we can get basic info from contacts or just display the fingerprint
          const contacts = await apiClient.getContacts();
          const contact = contacts.find(c => c.fingerprint === viewFingerprint);
          
          if (contact) {
             setProfileUser(contact);
          } else {
             // If not a contact, we might need a way to fetch public profile info. 
             // For now, we will just show the fingerprint as the name if unknown
             const fetchedUser = await apiClient.getUserByFingerprint(viewFingerprint);
             setProfileUser(fetchedUser || { 
               displayName: 'Unknown User', 
               username: 'unknown', 
               fingerprint: viewFingerprint,
               avatarUrl: `https://api.dicebear.com/7.x/avataaars/svg?seed=${viewFingerprint}`
             });
          }
        } catch (err) {
          console.error(err);
        } finally {
          setLoadingProfile(false);
        }
      } else {
        setProfileUser(user);
      }
    };
    loadProfile();
  }, [viewFingerprint, user]);

  const startEditing = () => {
    if (!isMe) return;
    setEditData({
      displayName: user.displayName,
      avatarUrl: user.avatarUrl
    });
    setIsEditing(true);
  };

  const saveProfile = async () => {
    try {
      await apiClient.updateProfile(user.id, editData);
      setUser({ ...user, ...editData });
      setProfileUser({ ...user, ...editData });
      setIsEditing(false);
      toast.success("Profile updated successfully");
    } catch (error) {
      toast.error("Failed to update profile");
    }
  };

  const copyToClipboard = () => {
    const data = JSON.stringify({
      username: profileUser.username,
      fingerprint: profileUser.fingerprint,
      displayName: profileUser.displayName,
      avatarUrl: profileUser.avatarUrl
    });
    navigator.clipboard.writeText(data);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Identity copied to clipboard");
  };

  const handleScan = async () => {
    setScanning(true);
    // Simulate scanning delay
    setTimeout(async () => {
      try {
        // Simulate finding a user
        const mockUser = {
          username: `peer_${Math.floor(Math.random() * 1000)}`,
          displayName: "New Mesh Friend",
          fingerprint: `MESH-${Math.random().toString(36).substring(7).toUpperCase()}`
        };
        await apiClient.addContact(mockUser);
        toast.success(`Added ${mockUser.displayName} to contacts!`);
        navigate('/contacts');
      } catch (error) {
        toast.error("Failed to add contact");
      } finally {
        setScanning(false);
      }
    }, 2000);
  };

  if (!profileUser) return null;

  return (
    <div className="h-full flex flex-col bg-white dark:bg-slate-950 overflow-y-auto">
      {/* Edit Modal */}
      {isEditing && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4 animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-4">
              <h3 className="text-lg font-bold">Edit Profile</h3>
              <Button variant="ghost" size="icon" onClick={() => setIsEditing(false)}>
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>Display Name</Label>
                <Input 
                  value={editData.displayName} 
                  onChange={(e) => setEditData({...editData, displayName: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Avatar URL</Label>
                <div className="flex gap-2">
                  <Input 
                    value={editData.avatarUrl} 
                    onChange={(e) => setEditData({...editData, avatarUrl: e.target.value})}
                    className="flex-1"
                  />
                  <img src={editData.avatarUrl} alt="Preview" className="w-10 h-10 rounded-full bg-slate-100 object-cover" />
                </div>
                <p className="text-xs text-slate-500">Paste a URL for your profile picture</p>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button variant="outline" className="flex-1" onClick={() => setIsEditing(false)}>Cancel</Button>
              <Button className="flex-1 bg-violet-600 hover:bg-violet-700" onClick={saveProfile}>Save Changes</Button>
            </div>
          </div>
        </div>
      )}

      {/* Profile Header */}
      <div className="p-8 bg-violet-50 dark:bg-violet-900/10 border-b border-violet-100 dark:border-violet-900/20 flex flex-col items-center text-center space-y-3 relative shrink-0">
        {isMe && (
          <Button 
            variant="ghost" 
            size="icon" 
            className="absolute top-4 right-4 text-violet-600 hover:bg-violet-100 dark:hover:bg-violet-900/50"
            onClick={startEditing}
          >
            <Edit2 className="w-5 h-5" />
          </Button>
        )}
        
        <div 
          className={`relative group ${isMe ? 'cursor-pointer' : ''}`} 
          onClick={startEditing}
        >
          <img 
            src={profileUser.avatarUrl} 
            alt={profileUser.displayName} 
            className="w-24 h-24 rounded-full border-4 border-white dark:border-slate-900 shadow-xl object-cover"
          />
          <div className="absolute bottom-1 right-1 w-6 h-6 bg-green-500 rounded-full border-2 border-white dark:border-slate-900" title="Online" />
          {isMe && (
            <div className="absolute inset-0 bg-black/30 rounded-full opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
              <Edit2 className="w-6 h-6 text-white" />
            </div>
          )}
        </div>
        
        <div className={`group ${isMe ? 'cursor-pointer' : ''}`} onClick={startEditing}>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center justify-center gap-2">
            {profileUser.displayName}
            {isMe && <Edit2 className="w-4 h-4 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />}
          </h2>
          <p className="text-violet-600 dark:text-violet-400 font-medium">@{profileUser.username}</p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-900 rounded-full border border-slate-200 dark:border-slate-800 shadow-sm max-w-full">
           <span className="text-[10px] font-mono text-slate-500 truncate max-w-[200px]">
             {profileUser.fingerprint}
           </span>
           <Copy className="w-3 h-3 text-slate-400 cursor-pointer hover:text-violet-600" onClick={copyToClipboard} />
        </div>
      </div>

      {/* Tabs (Only show Scan tab if it's ME) */}
      {isMe && (
        <div className="flex p-1 mx-6 mt-6 bg-slate-100 dark:bg-slate-900 rounded-xl">
          <button
            onClick={() => setActiveTab('code')}
            className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all flex items-center justify-center gap-2 ${
              activeTab === 'code'
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <QrCode className="w-4 h-4" />
            My Code
          </button>
          <button
            onClick={() => setActiveTab('scan')}
            className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all flex items-center justify-center gap-2 ${
              activeTab === 'scan'
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <Camera className="w-4 h-4" />
            Scan Camera
          </button>
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 p-6 flex flex-col items-center">
        {activeTab === 'code' ? (
          <div className="w-full max-w-sm bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-xl text-center space-y-6">
            <div className="bg-white p-4 rounded-2xl inline-block mx-auto">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(JSON.stringify({
                  username: profileUser.username,
                  fingerprint: profileUser.fingerprint,
                  displayName: profileUser.displayName,
                  avatarUrl: profileUser.avatarUrl
                }))}`}
                alt="QR Code"
                className="w-full h-auto rounded-lg"
              />
            </div>
            <div>
              <p className="text-sm text-slate-500 mb-4">
                Scan this code to verify identity and start an encrypted chat.
              </p>
              <Button 
                variant="outline" 
                className="w-full gap-2"
                onClick={copyToClipboard}
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy Identity String'}
              </Button>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-sm aspect-[3/4] bg-slate-950 rounded-3xl relative overflow-hidden flex flex-col items-center justify-center group">
             <div className="absolute inset-0 opacity-50">
               <div className="w-full h-full bg-[url('https://images.unsplash.com/photo-1516321165247-4aa89a48df28?w=800&q=80')] bg-cover bg-center" />
             </div>
             <ScanLine className="w-64 h-64 text-violet-500 animate-pulse absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
             
             <div className="absolute bottom-8 left-0 right-0 px-8">
               <Button 
                 size="default" 
                 className="w-full bg-violet-600 hover:bg-violet-700 text-white rounded-xl h-14"
                 onClick={handleScan}
                 disabled={scanning}
               >
                 {scanning ? 'Scanning...' : 'Simulate Scan'}
               </Button>
             </div>
          </div>
        )}
      </div>
    </div>
  );
}