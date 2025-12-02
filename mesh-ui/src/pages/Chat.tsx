import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useApp } from '@/components/context/AppContext';
import { apiClient } from '@/components/services/apiClient';
import MessageBubble from '@/components/chat/MessageBubble';
import { ArrowLeft, Send, Phone, Video, MoreVertical, Cat, Loader2, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const conversationId = searchParams.get('id');
  const navigate = useNavigate();
  const { user } = useApp();
  
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (conversationId && user) {
      loadChat();
      const interval = setInterval(refreshMessages, 3000); // Poll for new messages
      return () => clearInterval(interval);
    } else if (!conversationId) {
        navigate('/');
    }
  }, [conversationId, user]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadChat = async () => {
    try {
      setLoading(true);
      // Get conversation details
      const convos = await apiClient.getConversations();
      const conv = convos.find(c => c.id === conversationId);
      if (conv) {
        setConversation(conv);
        // Get messages
        const msgs = await apiClient.getMessages(conversationId);
        setMessages(msgs);
      } else {
        toast.error("Conversation not found");
        navigate('/');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const refreshMessages = async () => {
    if (!conversationId) return;
    const msgs = await apiClient.getMessages(conversationId);
    // Simple diff check could be better but simulating update
    setMessages(prev => {
        if (prev.length !== msgs.length) return msgs;
        // Check if last status changed
        const lastPrev = prev[prev.length - 1];
        const lastNew = msgs[msgs.length - 1];
        if (lastPrev?.status !== lastNew?.status) return msgs;
        return prev;
    });
  };

  const handleDeleteMessage = async (messageId) => {
    try {
      setMessages(prev => prev.filter(m => m.id !== messageId)); // Optimistic update
      await apiClient.deleteMessage(messageId);
      toast.success("Message deleted");
    } catch (e) {
      toast.error("Failed to delete message");
      refreshMessages(); // Revert if failed
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || sending) return;

    const text = inputText.trim();
    setInputText(''); // Optimistic clear
    setSending(true);

    try {
      // Optimistic add
      const tempMsg = {
        id: 'temp-' + Date.now(),
        text,
        from: 'me',
        status: 'sending',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, tempMsg]);
      scrollToBottom();

      // Send
      await apiClient.sendMessage(conversationId, text, conversation.contact.fingerprint);
      
      // Refresh to get real ID and status
      refreshMessages();
    } catch (e) {
      toast.error("Failed to send message");
      setMessages(prev => prev.filter(m => m.id.toString().startsWith('temp-') === false)); // Revert optimistic
    } finally {
      setSending(false);
    }
  };

  if (!user || !conversation) return null;

  return (
    <div className="flex flex-col h-full bg-[#e5e5ea] dark:bg-slate-950 relative">
      {/* Header */}
      <div className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 sticky top-0 z-20 shadow-sm">
        <div className="flex items-center gap-3">
          
          <Button 
            variant="default" 
            size="icon" 
            className="md -ml-2 text-slate-600"
            onClick={() => navigate('/chatlist')}
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
  
          <Link to={`/profile?id=${conversation.contact.fingerprint}`} className="flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 p-1 rounded-lg transition-colors">
            <div className="relative">
                <img 
                src={conversation.contact.avatarUrl} 
                className="w-10 h-10 rounded-full bg-slate-200 object-cover" 
                alt="Avatar"
                />
                <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-white dark:border-slate-900"></div>
            
            </div>
            
            <div>
                <h2 className="font-bold text-sm md:text-base text-slate-900 dark:text-white leading-tight">
                {conversation.contact.displayName}
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                @{conversation.contact.username}
                </p>
            </div>
          </Link>
        </div>

        {/* Text only - no voice/video icons */}
        <div className="w-10" />
      </div>

      {/* Messages Area */}
      <div 
        className="flex-1 overflow-y-auto p-4 space-y-2 scroll-smooth" 
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M54.627 0l.83.828-1.415 1.415-.828-.828-.828.828-1.415-1.415.828-.828-.828-.828 1.415-1.415.828.828.828-.828 1.415 1.415-.828.828zM22.485 0l.83.828-1.415 1.415-.828-.828-.828.828-1.415-1.415.828-.828-.828-.828 1.415-1.415.828.828.828-.828 1.415 1.415-.828.828zM0 22.485l.828.83-1.415 1.415-.828-.828-.828.828L-2.83 22.485l.828-.828-.828-.828 1.415-1.415.828.828.828-.828 1.415 1.415-.828.828zM0 54.627l.828.83-1.415 1.415-.828-.828-.828.828L-2.83 54.627l.828-.828-.828-.828 1.415-1.415.828.828.828-.828 1.415 1.415-.828.828zM54.627 60l.83-.828-1.415-1.415-.828.828-.828-.828-1.415 1.415.828.828-.828.828 1.415 1.415-.828-.828.828.828 1.415-1.415.828-.828zM22.485 60l.83-.828-1.415-1.415-.828.828-.828-.828-1.415 1.415.828.828-.828.828 1.415 1.415-.828-.828.828.828 1.415-1.415.828-.828z' fill='%239C92AC' fill-opacity='0.05' fill-rule='evenodd'/%3E%3C/svg%3E")` }}
      >
        {loading && messages.length === 0 ? (
          <div className="flex justify-center p-4"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>
        ) : messages.length === 0 ? (
           <div className="flex flex-col items-center justify-center h-full text-slate-400 opacity-60">
              <Cat className="w-12 h-12 mb-2" />
              <p className="text-sm">No messages yet. Say hello!</p>
           </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble 
              key={msg.id} 
              message={msg} 
              isMe={msg.from === 'me' || msg.from === user.fingerprint}
              onDelete={() => handleDeleteMessage(msg.id)}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Composer */}
      <div className="p-3 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 md:pb-3 pb-safe sticky bottom-0 z-20">
        <form 
            onSubmit={handleSend} 
            className="flex items-end gap-2 max-w-4xl mx-auto"
            onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend(e);
                }
            }}
        >
          <Input
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 bg-slate-100 dark:bg-slate-800 border border-violet-300 dark:border-violet-700 rounded-2xl min-h-[44px] py-3 focus-visible:ring-1 focus-visible:ring-violet-500"
            autoComplete="off"
          />
          <Button 
            type="submit" 
            size="icon"
            disabled={!inputText.trim() || sending}
            className={cn(
              "rounded-full h-11 w-11 transition-all duration-200 shadow-lg",
              inputText.trim() 
                ? "bg-violet-600 hover:bg-violet-700 text-white scale-100" 
                : "bg-slate-200 dark:bg-slate-800 text-slate-400 scale-95"
            )}
          >
             {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5 ml-0.5" />}
          </Button>
        </form>
      </div>
    </div>
  );
}