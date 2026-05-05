import React, { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import TopNavBar from '../components/TopNavBar';
import MapView from '../components/MapView';
import RightPanel from '../components/RightPanel';
import TopLocationsPanel from '../components/TopLocationsPanel';
import LocationDetailPanel from '../components/LocationDetailPanel';
import { generateMapData, explainResults, queryChat, getLocations } from '../services/api';

const heatmapFactors = [
  { key: 'footfall', label: 'Footfall', color: '#c2652a' },
  { key: 'youth', label: 'Youth', color: '#2f855a' },
  { key: 'rent', label: 'Rent', color: '#8b5cf6' },
  { key: 'access', label: 'Access', color: '#0284c7' },
  { key: 'competition', label: 'Competition', color: '#dc2626' },
  { key: 'flood', label: 'Flood', color: '#0f766e' },
  { key: 'traffic', label: 'Traffic', color: '#d97706' },
];

const Dashboard = () => {
  const location = useLocation();
  const initialQuery = location.state?.query || '';
  const initialMessages = location.state?.messages || [];
  const initialChatId = location.state?.chatId || localStorage.getItem('sentinelChatId');

  const [areas, setAreas] = useState([]);
  const [locations, setLocations] = useState([]);
  const [explanation, setExplanation] = useState('');
  const [loadingMap, setLoadingMap] = useState(true);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [heatmapFactor, setHeatmapFactor] = useState('footfall');
  const [heatmapOpen, setHeatmapOpen] = useState(true);
  const [heatmapEnabled, setHeatmapEnabled] = useState(true);
  
  // Chat state
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatId, setChatId] = useState(initialChatId);

  // Location detail view state
  const [selectedLocation, setSelectedLocation] = useState(null);

  useEffect(() => {
    const fetchLocations = async () => {
      try {
        const dataset = await getLocations();
        setLocations(Array.isArray(dataset) ? dataset : []);
      } catch (error) {
        console.error('Error fetching dataset locations:', error);
      }
    };

    fetchLocations();
  }, []);

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

        const explainData = await explainResults({ query: initialQuery, areas: mapData.areas || [] });
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
      const result = await queryChat({ message: userMessage, chatId });
      if (result.chat_id) {
        setChatId(result.chat_id);
        localStorage.setItem('sentinelChatId', result.chat_id);
      }
      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: result.text || 'Analysis complete.' }
      ]);

      // If the query asks for a new map generation, we could potentially re-trigger the map logic here
      // if result.is_clear is true
      if (result.filters) {
        setLoadingMap(true);
        const mapData = await generateMapData(userMessage);
        setAreas(mapData.areas || []);
        
        setLoadingMap(false);
        setLoadingExplanation(true);
        
        const explainData = await explainResults({ query: userMessage, areas: mapData.areas || [] });
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

  const handleViewDetails = (area) => {
    setSelectedLocation(area);
  };

  const handleCloseDetails = () => {
    setSelectedLocation(null);
  };

  const heatPoints = useMemo(() => {
    return locations
      .map((locationItem) => {
        const lat = Number(locationItem?.lat);
        const lng = Number(locationItem?.lng);
        const factorValue = Number(locationItem?.[heatmapFactor]);

        if (!Number.isFinite(lat) || !Number.isFinite(lng) || !Number.isFinite(factorValue)) {
          return null;
        }

        return [lat, lng, Math.min(1, Math.max(0, factorValue / 10))];
      })
      .filter(Boolean);
  }, [locations, heatmapFactor]);

  const heatmapLabel = useMemo(() => {
    return heatmapFactors.find((factor) => factor.key === heatmapFactor)?.label || 'Footfall';
  }, [heatmapFactor]);

  const heatmapMeta = useMemo(() => {
    return heatmapFactors.find((factor) => factor.key === heatmapFactor) || heatmapFactors[0];
  }, [heatmapFactor]);

  return (
    <div className="min-h-screen flex flex-col bg-background relative overflow-hidden">
      <TopNavBar />
      
      <main className="flex-grow flex flex-col lg:flex-row p-4 lg:p-6 gap-6 h-[calc(100vh-73px)]">
        {selectedLocation ? (
          /* Full-width Location Detail View (replaces LHS + Map + RHS) */
          <LocationDetailPanel
            area={selectedLocation}
            onClose={handleCloseDetails}
            query={initialQuery}
            conversation={messages}
          />
        ) : (
          /* Default Dashboard Layout */
          <>
            {/* Left Side: Top Locations */}
            <div className="w-full lg:w-1/4 h-full overflow-hidden">
              <TopLocationsPanel
                areas={areas}
                explanation={explanation}
                loadingExplanation={loadingExplanation}
                onViewDetails={handleViewDetails}
                heatmapFactors={heatmapFactors}
                heatmapFactor={heatmapFactor}
                onHeatmapFactorChange={setHeatmapFactor}
                heatmapOpen={heatmapOpen}
                onToggleHeatmapOpen={() => setHeatmapOpen((current) => !current)}
                heatmapEnabled={heatmapEnabled}
                onToggleHeatmapEnabled={() => setHeatmapEnabled((current) => !current)}
              />
            </div>

            {/* Center: Map Container */}
            <div className="w-full lg:w-2/4 h-full relative">
              {loadingMap && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-surface-container-low/80 backdrop-blur-sm rounded-2xl border border-outline-variant/50">
                  <span className="material-symbols-outlined animate-spin text-4xl text-primary mb-4">refresh</span>
                  <h3 className="font-headline text-2xl font-bold text-on-surface">Generating map...</h3>
                  <p className="font-body text-on-surface-variant mt-2">Plotting geospatial data for: "{initialQuery}"</p>
                </div>
              )}
              <MapView
                areas={areas}
                heatPoints={heatPoints}
                heatFactorKey={heatmapMeta.key}
                heatFactorLabel={heatmapLabel}
                heatFactorColor={heatmapMeta.color}
                heatmapEnabled={heatmapEnabled}
              />
            </div>

            {/* Right Side: Chat + Insights */}
            <div className="w-full lg:w-1/4 h-full overflow-hidden">
              <RightPanel
                messages={messages}
                input={input}
                setInput={setInput}
                onSubmit={handleChatSubmit}
                chatLoading={chatLoading}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
