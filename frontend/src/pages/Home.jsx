import React from 'react';
import { useNavigate } from 'react-router-dom';
import TopNavBar from '../components/TopNavBar';
import Footer from '../components/Footer';

const Home = () => {
  const navigate = useNavigate();

  return (
    <>
      <TopNavBar />
      <main className="flex-grow">
        <section className="max-w-7xl mx-auto px-6 py-24 md:py-32 flex flex-col md:flex-row items-center gap-12">
          <div className="md:w-1/2 space-y-8">
            <h1 className="font-headline text-5xl md:text-6xl lg:text-7xl leading-tight text-on-surface font-semibold tracking-tight">
              AI-Powered Geospatial <br /><span className="text-primary italic">Decision Intelligence</span>
            </h1>
            <p className="font-body text-lg md:text-xl text-on-surface-variant max-w-lg leading-relaxed font-light">
              Elevate urban planning and resource allocation. Leverage advanced natural language processing and
              real-time mapping to decode complex spatial data into actionable, sun-baked insights.
            </p>
            <div className="pt-4">
              <button
                onClick={() => navigate('/query')}
                className="bg-primary text-on-primary font-body font-medium px-8 py-4 rounded-lg shadow-soft hover:bg-primary-container hover:text-on-primary-container transition-colors duration-300">
                Start Analysis
              </button>
            </div>
          </div>
          <div className="md:w-1/2 w-full">
            <div className="relative w-full aspect-square md:aspect-[4/3] rounded-2xl overflow-hidden shadow-soft border border-outline-variant/30">
              <img
                alt="Geospatial Map Concept"
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBsU45oDU3snmKVxfUwO8iY813bm5nF5bdKIqfEp4V2O06sJ3_ceqaVJ7nkmHWhCg5fBJ4c7w2g8HehHyH6BdlpeXXUl5ta0f2d6L4vljH8U1gxCHstJEQyMZ6xUPDOWkI3i2SMnyFnTYFlm2Y1V7mnk-DX3iOMZwPbl3v58BlYMPBjenY2GKefAf5ubPOSNnYVje--qfYUaQ46dHVWncPuUo4yM_VU3Z9edyCnxDyq6Oz-PEhF_AMoeBKsEzTLNo8XlzosSuU9OA"
              />
            </div>
          </div>
        </section>

        {/* Features Bento Grid */}
        <section className="max-w-7xl mx-auto px-6 py-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[300px]">
            {/* Card 1: Large Span */}
            <div className="md:col-span-2 bg-surface-container-low rounded-2xl p-8 border border-outline-variant/50 shadow-soft flex flex-col justify-between relative overflow-hidden group">
              <div className="relative z-10 space-y-4">
                <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-6">
                  <span className="material-symbols-outlined text-2xl">map</span>
                </div>
                <h3 className="font-headline text-3xl font-medium text-on-surface">Smart Location Analysis</h3>
                <p className="font-body text-on-surface-variant max-w-md">
                  Evaluate optimal sites using multi-layered demographic, topographic, and economic data models.
                </p>
              </div>
              <div className="absolute bottom-0 right-0 w-2/3 h-2/3 opacity-20 group-hover:opacity-40 transition-opacity duration-500">
                <img
                  alt="Abstract architectural model"
                  className="w-full h-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzcGFfhedR_8gtet50aV-dK-Vw4Vr2Sv2TTg3wkou9jbLZh-9MN5ICYiDI4zceRZQKaISHmAwyD1beRnFKAf5-hB7xkujMTo4jKRsN7t2VGA_RzD4IGC1J185ePXXjmRRfAuDd8BEXVI3AEARL7SmQia7MaZGkPFxYyTUwIYj0pi--z7tguY75b4KFYYxaWw0otJ9ZtDL9_I4byHwCiC5relMjL2TuVjRw0ecoIFhMgWAZ99qP1L57oIkMJq8tKkqZzgusEmfeVg"
                />
              </div>
            </div>

            {/* Card 2 */}
            <div className="bg-surface-container rounded-2xl p-8 border border-outline-variant/30 shadow-soft flex flex-col">
              <div className="h-10 w-10 bg-surface text-tertiary rounded-full flex items-center justify-center mb-6 shadow-sm">
                <span className="material-symbols-outlined">local_fire_department</span>
              </div>
              <h3 className="font-headline text-2xl font-medium text-on-surface mb-3">Real-time Heatmaps</h3>
              <p className="font-body text-sm text-on-surface-variant flex-grow">
                Visualize population density, traffic flow, and environmental changes as they happen.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-surface-container rounded-2xl p-8 border border-outline-variant/30 shadow-soft flex flex-col">
              <div className="h-10 w-10 bg-surface text-primary rounded-full flex items-center justify-center mb-6 shadow-sm">
                <span className="material-symbols-outlined">forum</span>
              </div>
              <h3 className="font-headline text-2xl font-medium text-on-surface mb-3">NLP Query Engine</h3>
              <p className="font-body text-sm text-on-surface-variant flex-grow">
                Ask complex spatial questions in plain English and receive instant visual answers.
              </p>
            </div>

            {/* Card 4: Span 2 */}
            <div className="md:col-span-2 bg-surface-container-high rounded-2xl p-8 border border-outline-variant/40 shadow-soft flex items-center gap-8">
              <div className="flex-grow space-y-4">
                <div className="h-10 w-10 bg-surface text-on-surface rounded-full flex items-center justify-center mb-4 shadow-sm">
                  <span className="material-symbols-outlined">account_tree</span>
                </div>
                <h3 className="font-headline text-2xl font-medium text-on-surface">Decision Support System</h3>
                <p className="font-body text-on-surface-variant">
                  Simulate scenarios and predict outcomes with our proprietary AI models designed specifically for urban topology.
                </p>
              </div>
              <div className="hidden md:block w-1/3 aspect-square rounded-xl overflow-hidden opacity-80">
                <img
                  alt="Data visualization graph"
                  className="w-full h-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBoM3-Tdpu6IKFAjUZNxnWdsaEc6v6sDdeu-jZk4BBQx1-hQ8SeE-vbNojfR8g5d3RuvY2yj8MQJo70uUEKwutJ07nLuJRqUyAHAfgHMxLxUBLMOWS3npM4JbRJYu6WQs-BaCZdvALL5y_0tUUXorhErG6bHQgZYc_OIGFzZQ0hD1Gp74-rCre5_BZ7GvTKHoQWMCPZ9wKhCD8AN4fdzXJvqVEMxAlcRkWhZtBtjfyy6Xxa_zXTzgTNqkpG9jf1ntsG5sJPgLrDHw"
                />
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
};

export default Home;
