import React from 'react';
import TopNavBar from '../components/TopNavBar';
import SafetyMap from '../components/SafetyMap';

const CrimeMap = () => {
  return (
    <div className="min-h-screen flex flex-col bg-background relative overflow-hidden">
      <TopNavBar />
      <main className="flex-grow p-4 lg:p-6 h-[calc(100vh-73px)] min-h-0 overflow-hidden">
        <div className="h-full w-full min-h-0 overflow-hidden">
          <SafetyMap />
        </div>
      </main>
    </div>
  );
};

export default CrimeMap;