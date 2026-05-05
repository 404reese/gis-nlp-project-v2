import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import TopNavBar from '../components/TopNavBar';
import Footer from '../components/Footer';
import ChatBox from '../components/ChatBox';
import { queryChat, listChats, getChat } from '../services/api';

const Query = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [chatId, setChatId] = useState(() => {
    return localStorage.getItem('sentinelChatId');
  });
  const navigate = useNavigate();

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const data = await listChats();
      setHistory(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadChatById = async (id) => {
    if (!id) return;
    try {
      const data = await getChat(id);
      const mapped = (data.messages || []).map((msg) => ({
        sender: msg.role === 'assistant' ? 'ai' : 'user',
        text: msg.text || ''
      }));
      setMessages(mapped);
      setChatId(data.chat_id);
      localStorage.setItem('sentinelChatId', data.chat_id);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleSubmit = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { sender: 'user', text: userMessage }]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const result = await queryChat({ message: userMessage, chatId });
      if (result.chat_id) {
        setChatId(result.chat_id);
        localStorage.setItem('sentinelChatId', result.chat_id);
      }

      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: result.text || 'Analysis complete.' }
      ]);

      if (result.filters) {
        // Short delay so user can read the success message before navigating
        setTimeout(() => {
          navigate('/dashboard', {
            state: {
              query: userMessage,
              messages: [
                ...messages,
                { sender: 'user', text: userMessage },
                { sender: 'ai', text: result.text || 'Analysis complete.' }
              ],
              chatId: result.chat_id || chatId
            }
          });
        }, 1500);
      }

      await loadHistory();
    } catch (err) {
      console.error(err);
      setError('Failed to analyze the query. Please try again.');
      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: 'Error: Could not reach the analysis service. Is the backend running?' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <TopNavBar />
      <main className="flex-grow p-6 bg-background">
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
          <aside className="bg-surface-container-low rounded-2xl border border-outline-variant/50 shadow-soft p-4 h-fit lg:sticky lg:top-24">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-headline text-xl text-on-surface">Chat History</h2>
              <button
                type="button"
                onClick={() => {
                  setMessages([]);
                  setChatId(null);
                  localStorage.removeItem('sentinelChatId');
                }}
                className="text-xs font-body text-on-surface-variant hover:text-on-surface"
              >
                New chat
              </button>
            </div>

            {historyLoading ? (
              <div className="text-sm font-body text-on-surface-variant">Loading chats...</div>
            ) : history.length === 0 ? (
              <div className="text-sm font-body text-on-surface-variant">No chats yet.</div>
            ) : (
              <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
                {history.map((chat) => (
                  <button
                    key={chat.chat_id}
                    type="button"
                    onClick={() => loadChatById(chat.chat_id)}
                    className={`w-full text-left rounded-xl p-3 border transition-colors ${
                      chat.chat_id === chatId
                        ? 'bg-primary text-on-primary border-primary/60'
                        : 'bg-surface text-on-surface border-outline-variant/40 hover:bg-surface-container'
                    }`}
                  >
                    <div className="font-body text-sm font-medium line-clamp-2">
                      {chat.title || 'Untitled chat'}
                    </div>
                    <div className="text-xs mt-2 opacity-80 line-clamp-1">
                      {chat.last_message || 'No messages yet'}
                    </div>
                    <div className="text-xs mt-1 opacity-60">
                      {chat.message_count} messages
                    </div>
                  </button>
                ))}
              </div>
            )}
          </aside>

          <section className="space-y-6">
            <div className="text-center space-y-2">
              <h1 className="font-headline text-4xl md:text-5xl text-on-surface font-semibold">
                Spatial Query Engine
              </h1>
              <p className="font-body text-on-surface-variant">
                Describe the geospatial analysis you want to perform in plain English.
              </p>
            </div>

            {error && (
              <div className="bg-error-container text-on-error-container p-4 rounded-lg font-body text-sm border border-error/30">
                {error}
              </div>
            )}

            <ChatBox
              messages={messages}
              input={input}
              setInput={setInput}
              onSubmit={handleSubmit}
              loading={loading}
              className="h-[60vh] md:h-[600px]"
            />
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
};

export default Query;
