import React from 'react';
import TopNavBar from '../components/TopNavBar';
import Footer from '../components/Footer';

const HowItWorks = () => {
  return (
    <>
      <TopNavBar />
      <main className="flex-grow bg-surface-container-low">
        {/* Hero Section */}
        <section className="max-w-4xl mx-auto px-6 py-16 md:py-24">
          <h1 className="font-headline text-5xl md:text-6xl font-semibold text-on-surface mb-6">
            How This Works
          </h1>
          <p className="font-body text-lg text-on-surface-variant max-w-2xl leading-relaxed">
            Discover the data engineering, processing pipeline, and scoring mechanisms behind our AI-powered 
            geospatial decision intelligence platform.
          </p>
        </section>

        {/* Content */}
        <section className="max-w-4xl mx-auto px-6 pb-24">
          {/* Section 1: Data Engineering & Overview */}
          <div className="space-y-12">
            {/* Section 1 */}
            <article className="space-y-6">
              <div className="flex gap-4 items-start">
                <div className="flex-1">
                  <h2 className="font-headline text-3xl font-semibold text-on-surface mb-4">
                    Data Engineering & Feature Generation
                  </h2>
                </div>
              </div>

              <div className="bg-surface-container rounded-xl p-8 space-y-6 border border-outline-variant/30">
                <div>
                  <h3 className="font-headline text-xl font-medium text-on-surface mb-4">
                    1. Overview
                  </h3>
                  <p className="font-body text-on-surface-variant leading-relaxed mb-3">
                    The system uses a combination of <span className="font-semibold text-on-surface">real-world open datasets</span> and{' '}
                    <span className="font-semibold text-on-surface">derived (synthetic) indicators</span> to evaluate locations across Mumbai.
                  </p>
                  <p className="font-body text-on-surface-variant leading-relaxed">
                    Each location is represented using normalized scores (0–10) for multiple decision factors such as 
                    footfall, rent, accessibility, and competition.
                  </p>
                </div>
              </div>
            </article>

            {/* Section 2: Data Sources */}
            <article className="space-y-6">
              <div className="flex gap-4 items-start">
                <div className="flex-1">
                  <h2 className="font-headline text-3xl font-semibold text-on-surface mb-4">
                    Data Sources
                  </h2>
                </div>
              </div>

              <div className="grid gap-4">
                {/* Data Source 1 */}
                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <h4 className="font-headline text-lg font-medium text-on-surface">Population Density</h4>
                  <div className="space-y-2 text-on-surface-variant">
                    <p className="font-body"><span className="font-semibold">Source:</span> <a href="https://data.humdata.org/dataset/pakistan-india_all-files-high-resolution-population-density-maps" target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary-container transition-colors">HumData (High Resolution Population Density Maps)</a></p>
                    <p className="font-body"><span className="font-semibold">Used to estimate:</span> <span className="text-on-surface">Footfall potential</span></p>
                    <p className="font-body"><span className="text-primary">Higher density ⇒ higher commercial viability</span></p>
                  </div>
                </div>

                {/* Data Source 2 */}
                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <h4 className="font-headline text-lg font-medium text-on-surface">Internet & Activity Proxy</h4>
                  <div className="space-y-2 text-on-surface-variant">
                    <p className="font-body"><span className="font-semibold">Source:</span> <a href="https://www.ookla.com/ookla-for-good/open-data" target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary-container transition-colors">Ookla Open Data</a></p>
                    <p className="font-body"><span className="font-semibold">Used as a proxy for:</span></p>
                  <ul className="space-y-1">
                    <li className="font-body">• Digital activity</li>
                    <li className="font-body">• Urban development</li>
                  </ul>
                    <p className="font-body"><span className="text-primary">Higher speeds ⇒ higher economic activity</span></p>
                  </div>
                </div>

                {/* Data Source 3 */}
                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <h4 className="font-headline text-lg font-medium text-on-surface">Map & Infrastructure Data</h4>
                  <div className="space-y-2 text-on-surface-variant">
                    <p className="font-body"><span className="font-semibold">Source:</span> OpenStreetMap (OSM)</p>
                    <p className="font-body"><span className="font-semibold">Extracted using:</span> PostGIS</p>
                    <p className="font-body"><span className="font-semibold">Used for:</span></p>
                    <ul className="space-y-1">
                      <li className="font-body">• Road networks → accessibility</li>
                      <li className="font-body">• POIs → competition</li>
                      <li className="font-body">• Transport hubs → connectivity</li>
                    </ul>
                  </div>
                </div>

                {/* Data Source 4: Synthetic */}
                <div className="bg-primary/5 rounded-xl p-6 border border-primary/20 space-y-3">
                  <h4 className="font-headline text-lg font-medium text-on-surface">Synthetic / Derived Data</h4>
                  <div className="space-y-2 text-on-surface-variant">
                    <p className="font-body">
                      Since some real-world data is not directly available:
                    </p>
                    <ul className="space-y-1">
                      <li className="font-body">• <span className="font-semibold">Rental Index</span> → estimated using area category</li>
                      <li className="font-body">• <span className="font-semibold">Youth Demographic</span> → inferred from urban zones (colleges, cafes, malls)</li>
                      <li className="font-body">• <span className="font-semibold">Competition Score</span> → based on POI density (shops, malls)</li>
                      <li className="font-body">• <span className="font-semibold">Flood Risk</span> → approximated from known low-lying regions</li>
                      <li className="font-body">• <span className="font-semibold">Traffic Score</span> → based on road density + known congestion zones</li>
                    </ul>
                  </div>
                  <div className="mt-4 p-4 bg-primary/10 rounded-lg border-l-4 border-primary">
                    <p className="font-body text-on-surface">
                      <span className="font-semibold">Key Insight:</span> This approach enables transparent, 
                      scientifically-grounded decision making even when direct data isn't available.
                    </p>
                  </div>
                </div>
              </div>
            </article>

            {/* Section 3: Data Processing Pipeline */}
            <article className="space-y-6">
              <div className="flex gap-4 items-start">
                <div className="flex-1">
                  <h2 className="font-headline text-3xl font-semibold text-on-surface mb-4">
                    Data Processing Pipeline
                  </h2>
                </div>
              </div>

              <div className="space-y-4">
                {/* Step 1 */}
                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-on-primary font-semibold text-sm">1</span>
                    <h4 className="font-headline text-lg font-medium text-on-surface">Data Cleaning</h4>
                  </div>
                  <ul className="space-y-1 text-on-surface-variant">
                    <li className="font-body">• Removed missing and inconsistent entries</li>
                    <li className="font-body">• Standardized coordinate format (lat/lng)</li>
                  </ul>
                </div>

                {/* Step 2 */}
                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-on-primary font-semibold text-sm">2</span>
                    <h4 className="font-headline text-lg font-medium text-on-surface">Feature Engineering</h4>
                  </div>
                  <p className="text-on-surface-variant font-body mb-3">
                    Raw data converted into meaningful indicators:
                  </p>
                  <div className="bg-surface-container-low rounded-lg p-4 space-y-2 font-mono text-sm text-on-surface-variant">
                    <p>Population Density → Footfall Score</p>
                    <p>POI Count → Competition Score</p>
                    <p>Road Density → Accessibility Score</p>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-on-primary font-semibold text-sm">3</span>
                    <h4 className="font-headline text-lg font-medium text-on-surface">Normalization</h4>
                  </div>
                  <p className="text-on-surface-variant font-body mb-3">
                    All features are scaled to <span className="font-semibold text-on-surface">0–10 range</span>:
                  </p>
                  <div className="bg-surface-container-low rounded-lg p-4 font-mono text-sm text-on-surface border-l-4 border-primary">
                    <p>normalized_value = (value - min) / (max - min) * 10</p>
                  </div>
                  <p className="text-on-surface-variant font-body text-sm mt-3">
                    This ensures consistency across different data types.
                  </p>
                </div>

                {/* Step 4 */}
                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-on-primary font-semibold text-sm">4</span>
                    <h4 className="font-headline text-lg font-medium text-on-surface">Final Dataset</h4>
                  </div>
                  <p className="text-on-surface-variant font-body mb-3">
                    Each location is stored as:
                  </p>
                  <div className="bg-surface-container-low rounded-lg p-4 font-mono text-xs text-on-surface overflow-x-auto">
                    <pre>{`{
  "name": "King Circle",
  "lat": 19.0280,
  "lng": 72.8580,
  "footfall": 7,
  "youth": 7,
  "rent": 7,
  "access": 9,
  "competition": 6,
  "flood": 5,
  "traffic": 8
}`}</pre>
                  </div>
                </div>
              </div>
            </article>

            {/* Section 4: Scoring Mechanism */}
            <article className="space-y-6">
              <div className="flex gap-4 items-start">
                <div className="flex-1">
                  <h2 className="font-headline text-3xl font-semibold text-on-surface mb-4">
                    Scoring Mechanism
                  </h2>
                </div>
              </div>

              <div className="bg-surface-container rounded-xl p-8 border border-outline-variant/30 space-y-6">
                <p className="font-body text-on-surface-variant">
                  Each location is evaluated using a weighted scoring model:
                </p>
                
                <div className="bg-primary/5 rounded-lg p-6 border border-primary/20 font-mono text-sm text-on-surface">
                  <p className="font-semibold mb-3">Score Calculation:</p>
                  <pre className="whitespace-pre-wrap text-xs md:text-sm">{`Score = 
  0.3  × Footfall +
  0.25 × Youth +
  0.2  × Accessibility +
  0.15 × (10 − Rent) +
  0.1  × (10 − Competition)`}</pre>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="bg-surface-container-low rounded-lg p-4 space-y-2">
                    <p className="font-semibold text-on-surface">Footfall</p>
                    <p className="text-xs text-on-surface-variant">30% weight - Primary commercial viability factor</p>
                  </div>
                  <div className="bg-surface-container-low rounded-lg p-4 space-y-2">
                    <p className="font-semibold text-on-surface">Youth</p>
                    <p className="text-xs text-on-surface-variant">25% weight - Target demographic availability</p>
                  </div>
                  <div className="bg-surface-container-low rounded-lg p-4 space-y-2">
                    <p className="font-semibold text-on-surface">Accessibility</p>
                    <p className="text-xs text-on-surface-variant">20% weight - Infrastructure connectivity</p>
                  </div>
                  <div className="bg-surface-container-low rounded-lg p-4 space-y-2">
                    <p className="font-semibold text-on-surface">Rent & Competition</p>
                    <p className="text-xs text-on-surface-variant">15% + 10% - Operational cost factors</p>
                  </div>
                </div>
              </div>
            </article>

            {/* Section 5: Why This Works */}
            <article className="space-y-6">
              <div className="flex gap-4 items-start">
                <div className="flex-1">
                  <h2 className="font-headline text-3xl font-semibold text-on-surface mb-4">
                    Why This Approach Works
                  </h2>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <div>
                    <h4 className="font-headline font-semibold text-on-surface mb-2">Hybrid Data Model</h4>
                    <p className="font-body text-sm text-on-surface-variant">
                      Combines real datasets with intelligently derived indicators for complete coverage
                    </p>
                  </div>
                </div>

                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <div>
                    <h4 className="font-headline font-semibold text-on-surface mb-2">Fast Computation</h4>
                    <p className="font-body text-sm text-on-surface-variant">
                      No heavy external APIs needed - enables real-time decision support
                    </p>
                  </div>
                </div>

                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <div>
                    <h4 className="font-headline font-semibold text-on-surface mb-2">Explainable Results</h4>
                    <p className="font-body text-sm text-on-surface-variant">
                      Transparent scoring mechanism that users can understand and verify
                    </p>
                  </div>
                </div>

                <div className="bg-surface-container rounded-xl p-6 border border-outline-variant/30 space-y-3">
                  <div>
                    <h4 className="font-headline font-semibold text-on-surface mb-2">Actionable Intelligence</h4>
                    <p className="font-body text-sm text-on-surface-variant">
                      Suitable for real-world business and urban planning decisions
                    </p>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
};

export default HowItWorks;
