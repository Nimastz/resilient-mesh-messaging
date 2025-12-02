import { base44 } from "@/api/base44Client";

// Simulation of the backend API using Base44 entities
const SIMULATED_DELAY = 600;
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const apiClient = {
  // Profile
  getProfile: async () => {
    await sleep(SIMULATED_DELAY);
    const userId = localStorage.getItem('mesh_user_id');
    if (!userId) return null;

    try {
      // Try to fetch specific user if we have ID
      const profiles = await base44.entities.UserProfile.list();
      const user = profiles.find(p => p.id === userId);
      return user || null;
    } catch (e) {
      return null;
    }
  },

  login: async (username, password) => {
    await sleep(SIMULATED_DELAY);
    const profiles = await base44.entities.UserProfile.list();
    const user = profiles.find(p => (p.username === username || p.username === '@' + username) && p.password === password);
    if (user) {
      localStorage.setItem('mesh_user_id', user.id);
      return user;
    }
    throw new Error("Invalid username or password");
  },

  logout: async () => {
    localStorage.removeItem('mesh_user_id');
  },

  createProfile: async (data) => {
    await sleep(SIMULATED_DELAY);
    const profiles = await base44.entities.UserProfile.list();
    if (profiles.some(p => p.username === data.username)) {
      throw new Error("Username already exists");
    }
    const fingerprint = data.fingerprint || `MESH-${Math.random().toString(36).substring(2, 6).toUpperCase()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
    const newUser = await base44.entities.UserProfile.create({ ...data, fingerprint });
    localStorage.setItem('mesh_user_id', newUser.id);
    return newUser;
  },

  getUserByFingerprint: async (fingerprint) => {
    await sleep(SIMULATED_DELAY);
    const profiles = await base44.entities.UserProfile.list();
    return profiles.find(p => p.fingerprint === fingerprint);
  },

  updateProfile: async (id, data) => {
    await sleep(SIMULATED_DELAY);
    return await base44.entities.UserProfile.update(id, data);
  },

  // Contacts
  getContacts: async () => {
    await sleep(SIMULATED_DELAY);
    return await base44.entities.Contact.list();
  },

  addContact: async (data) => {
    await sleep(SIMULATED_DELAY);
    const existing = await base44.entities.Contact.list();
    const found = existing.find(c => c.username === data.username || c.fingerprint === data.fingerprint);
    if (found) throw new Error("Contact already exists");
    
    return await base44.entities.Contact.create({
      ...data,
      isBlocked: false,
      avatarUrl: data.avatarUrl || `https://api.dicebear.com/7.x/avataaars/svg?seed=${data.username}`
    });
  },

  // Conversations
  getConversations: async () => {
    await sleep(SIMULATED_DELAY);
    const convos = await base44.entities.Conversation.list('-lastMessageTime');
    const contacts = await base44.entities.Contact.list();
    return convos.map(c => {
      const contact = contacts.find(ct => ct.id === c.contactId);
      return { ...c, contact };
    });
  },

  getOrCreateConversation: async (contactId) => {
    const convos = await base44.entities.Conversation.list();
    let conv = convos.find(c => c.contactId === contactId);
    if (!conv) {
      conv = await base44.entities.Conversation.create({
        contactId,
        unreadCount: 0,
        lastMessageTime: new Date().toISOString()
      });
    }
    return conv;
  },

  // Messages
  getMessages: async (conversationId) => {
    return await base44.entities.Message.filter({ conversationId }, 'timestamp', 100);
  },

  sendMessage: async (conversationId, text, toFingerprint) => {
    await sleep(300);
    
    const msg = await base44.entities.Message.create({
      conversationId,
      text,
      from: 'me',
      to: toFingerprint,
      status: 'sending',
      timestamp: new Date().toISOString()
    });

    await base44.entities.Conversation.update(conversationId, {
      lastMessageText: text,
      lastMessageTime: msg.timestamp
    });

    // Simulate delivery lifecycle
    setTimeout(async () => {
      await base44.entities.Message.update(msg.id, { status: 'sent' });
      
      setTimeout(async () => {
         await base44.entities.Message.update(msg.id, { status: 'delivered' });
      }, 2000);
      
      // Simulate Reply
      setTimeout(async () => {
        await base44.entities.Message.create({
           conversationId,
           text: `Meow! I received: "${text}"`,
           from: toFingerprint,
           to: 'me',
           status: 'delivered',
           timestamp: new Date().toISOString()
        });
         await base44.entities.Conversation.update(conversationId, {
          lastMessageText: `Meow! I received: "${text}"`,
          lastMessageTime: new Date().toISOString()
        });
      }, 4000);

    }, 1500);

    return msg;
  },

  // System
  getRouterStats: async () => {
    await sleep(SIMULATED_DELAY);
    return {
      total_queued: Math.floor(Math.random() * 5),
      total_retries: Math.floor(Math.random() * 10),
      uptime: '2d 4h'
    };
  },

  getBlePeers: async () => {
    await sleep(SIMULATED_DELAY);
    return Array(Math.floor(Math.random() * 4) + 1).fill(0).map((_, i) => ({
      fingerprint: `PEER-${Math.random().toString(36).substring(7).toUpperCase()}`,
      rssi: -Math.floor(Math.random() * 60 + 30),
      last_seen: Date.now() - Math.floor(Math.random() * 10000)
    }));
  },

  // Delete operations
  deleteContact: async (id) => {
    await sleep(300);
    return await base44.entities.Contact.delete(id);
  },

  deleteConversation: async (id) => {
    await sleep(300);
    return await base44.entities.Conversation.delete(id);
  },

  deleteMessage: async (id) => {
    await sleep(300);
    return await base44.entities.Message.delete(id);
  }
};