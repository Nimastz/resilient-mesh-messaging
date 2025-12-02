// src/App.tsx
import { Routes, Route } from 'react-router-dom'
import Layout from '@/pages/Layout'
import Onboarding from '@/pages/Onboarding'
import Contacts from '@/pages/Contacts'
import Profile from '@/pages/Profile'
import ChatList from './pages/ChatList'
import Settings from '@/pages/Settings'
import SignIn from '@/pages/SignIn'
import Chat from '@/pages/Chat'
function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/chat" element={<Chat />} />
        <Route path="/chatlist" element={<ChatList />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/sign-in" element={<SignIn />} />
      </Routes>
    </Layout>
  )
}

export default App
