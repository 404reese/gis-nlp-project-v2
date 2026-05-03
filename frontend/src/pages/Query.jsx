import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import TopNavBar from '../components/TopNavBar';
import Footer from '../components/Footer';
import ChatBox from '../components/ChatBox';
import { analyzeQuery } from '../services/api';

const Query = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { sender: 'user', text: userMessage }]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const result = await analyzeQuery(userMessage);

      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: result.response || result.message || 'Analysis complete.' }
      ]);

      if (result.is_clear) {
        // Short delay so user can read the success message before navigating
        setTimeout(() => {
          navigate('/dashboard', { state: { query: userMessage, messages: [...messages, { sender: 'user', text: userMessage }, { sender: 'ai', text: result.response || result.message }] } });
        }, 1500);
      }
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
      <main className="flex-grow flex flex-col items-center justify-center p-6 bg-background">
        <div className="w-full max-w-3xl space-y-6">
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
        </div>
      </main>
      <Footer />
    </>
  );
};

export default Query;
