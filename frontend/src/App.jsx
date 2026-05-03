import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Query from './pages/Query';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/query" element={<Query />} />
      <Route path="/dashboard" element={<Dashboard />} />
    </Routes>
  );
}

export default App;
