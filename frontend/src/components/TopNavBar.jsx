import React from 'react';
import { Link } from 'react-router-dom';

const TopNavBar = () => {
  return (
    <nav className="bg-[#faf5ee] dark:bg-stone-900 border-b border-stone-200/60 dark:border-stone-800 shadow-[0_2px_16px_rgba(58,48,42,0.04)] sticky top-0 z-50">
      <div className="flex justify-between items-center w-full px-6 py-3 max-w-full">
        <div className="flex items-center gap-8">
          <Link to="/" className="font-['EB_Garamond'] text-2xl font-bold text-[#c2652a] dark:text-orange-500">
            Sentinel
          </Link>
        </div>
        <div className="flex items-center gap-4 text-[#c2652a] dark:text-orange-400">
          <button className="hover:text-[#c2652a] dark:hover:text-orange-300 transition-colors duration-200 ease-in-out">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="hover:text-[#c2652a] dark:hover:text-orange-300 transition-colors duration-200 ease-in-out">
            <span className="material-symbols-outlined">settings</span>
          </button>
          <img
            alt="User profile"
            className="h-8 w-8 rounded-full border border-outline-variant object-cover"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuDAu5UxLBYsVyuikAijel8i7uT9aO7isKqGMA6LVbY5VGpXxMHUtAKEt4ELqHCqoAR6X7NnlPQV11X-aJuv1Jqju4dpussa8U6f0nFpjpsVJTWyGR6X_PUpL4L2icSKcx1-931mIcphOlzlXy3brppHHjMYPHMROTjq3qQWWhEkWMXKuroUgGPguGEz4O9NlK1NRRof--Hi2x7jc038On_0NhICRtJZl3I6yhaRVbvvX76ah61A1ewsFzmsHlvv1fwmAtkPEmQVdg"
          />
        </div>
      </div>
    </nav>
  );
};

export default TopNavBar;
