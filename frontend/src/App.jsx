import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Query from './pages/Query';
import Dashboard from './pages/Dashboard';
import HowItWorks from './pages/HowItWorks';
import CrimeMap from './pages/CrimeMap';
import Studio from './pages/Studio';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/studio" element={<Studio />} />
      <Route path="/query" element={<Query />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/crimemap" element={<CrimeMap />} />
      <Route path="/how-it-works" element={<HowItWorks />} />
    </Routes>
  );
}

export default App;
