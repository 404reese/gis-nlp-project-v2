import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import TopNavBar from '../components/TopNavBar';
import MapView from '../components/MapView';
import RightPanel from '../components/RightPanel';
import ChatBox from '../components/ChatBox';
import { generateMapData, explainResults, analyzeQuery } from '../services/api';

const Dashboard = () => {
  const location = useLocation();
  const initialQuery = location.state?.query || '';
  const initialMessages = location.state?.messages || [];

  const [areas, setAreas] = useState([]);
  const [explanation, setExplanation] = useState('');
  const [loadingMap, setLoadingMap] = useState(true);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  
  // Chat state
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!initialQuery) {
        setLoadingMap(false);
        return;
      }

      setLoadingMap(true);
      try {
        const mapData = await generateMapData(initialQuery);
        const mapAreas = mapData.areas || [];
        setAreas(mapAreas);

        setLoadingMap(false);
        setLoadingExplanation(true);

        const explainData = await explainResults({ query: initialQuery, data: mapData });
        setExplanation(explainData.explanation);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoadingMap(false);
        setLoadingExplanation(false);
      }
    };

    fetchData();
  }, [initialQuery]);

  const handleChatSubmit = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { sender: 'user', text: userMessage }]);
    setInput('');
    setChatLoading(true);

    try {
      const result = await analyzeQuery(userMessage);
      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: result.response || result.message || 'Analysis complete.' }
      ]);
      
      // If the query asks for a new map generation, we could potentially re-trigger the map logic here
      // if result.is_clear is true
      if (result.is_clear) {
        setLoadingMap(true);
        const mapData = await generateMapData(userMessage);
        setAreas(mapData.areas || []);
        
        setLoadingMap(false);
        setLoadingExplanation(true);
        
        const explainData = await explainResults({ query: userMessage, data: mapData });
        setExplanation(explainData.explanation);
        setLoadingExplanation(false);
      }

    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: 'Error: Could not reach the analysis service.' }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background relative overflow-hidden">
      <TopNavBar />
      
      <main className="flex-grow flex flex-col lg:flex-row p-4 lg:p-6 gap-6 h-[calc(100vh-73px)]">
        {/* Left Side: Map Container */}
        <div className="w-full lg:w-2/3 h-full relative">
          {loadingMap && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-surface-container-low/80 backdrop-blur-sm rounded-2xl border border-outline-variant/50">
              <span className="material-symbols-outlined animate-spin text-4xl text-primary mb-4">refresh</span>
              <h3 className="font-headline text-2xl font-bold text-on-surface">Generating map...</h3>
              <p className="font-body text-on-surface-variant mt-2">Plotting geospatial data for: "{initialQuery}"</p>
            </div>
          )}
          <MapView areas={areas} />
        </div>

        {/* Right Side: Details Panel */}
        <div className="w-full lg:w-1/3 h-full overflow-hidden">
          <RightPanel 
            areas={areas} 
            explanation={explanation} 
            loadingExplanation={loadingExplanation} 
          />
        </div>
      </main>

      {/* Floating Chat Box Toggle */}
      <div className="fixed bottom-6 right-6 z-50">
        {!isChatOpen ? (
          <button 
            onClick={() => setIsChatOpen(true)}
            className="h-14 w-14 bg-primary text-on-primary rounded-full shadow-soft flex items-center justify-center hover:bg-primary-container transition-transform hover:scale-105 active:scale-95"
          >
            <span className="material-symbols-outlined text-2xl">chat</span>
          </button>
        ) : (
          <div className="relative w-80 sm:w-96 h-[500px] max-h-[80vh] flex flex-col shadow-2xl rounded-2xl overflow-hidden transition-all transform origin-bottom-right">
            <div className="bg-primary text-on-primary p-4 flex justify-between items-center rounded-t-2xl z-10">
              <h3 className="font-headline font-bold flex items-center gap-2">
                <span className="material-symbols-outlined">forum</span>
                Sentinel Assistant
              </h3>
              <button 
                onClick={() => setIsChatOpen(false)}
                className="hover:text-primary-container transition-colors"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            {/* Reusing ChatBox component */}
            <ChatBox
              messages={messages}
              input={input}
              setInput={setInput}
              onSubmit={handleChatSubmit}
              loading={chatLoading}
              className="flex-grow rounded-none rounded-b-2xl border-x border-b border-t-0 shadow-none h-full"
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
