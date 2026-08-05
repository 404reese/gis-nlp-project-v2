import React from 'react';
import { Link } from 'react-router-dom';

const TopNavBar = () => {
  return (
    <nav className="bg-[#faf5ee] dark:bg-stone-900 border-b border-stone-200/60 dark:border-stone-800 shadow-[0_2px_16px_rgba(58,48,42,0.04)] sticky top-0 z-50">
      <div className="flex justify-between items-center w-full px-6 py-3 max-w-full">
        <div className="flex items-center gap-12">
          <Link to="/" className="font-['EB_Garamond'] text-2xl font-bold text-[#c2652a] dark:text-orange-500 hover:opacity-80 transition-opacity">
            Sentinel
          </Link>
          <div className="hidden md:flex items-center gap-8 text-[#3a302a] dark:text-stone-100">
            <Link to="/studio" className="font-body font-semibold text-[#c2652a] dark:text-orange-400 hover:opacity-80 transition-colors duration-200">
              Studio ✦
            </Link>
            <Link to="/query" className="font-body hover:text-[#c2652a] dark:hover:text-orange-400 transition-colors duration-200">
              Query
            </Link>
            <Link to="/crimemap" className="font-body hover:text-[#c2652a] dark:hover:text-orange-400 transition-colors duration-200">
              Crime Map
            </Link>
            <Link to="/how-it-works" className="font-body hover:text-[#c2652a] dark:hover:text-orange-400 transition-colors duration-200">
              How It Works
            </Link>
          </div>
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
            src="https://uxwing.com/wp-content/themes/uxwing/download/peoples-avatars/default-avatar-profile-picture-male-icon.png"
          />
        </div>
      </div>
    </nav>
  );
};

export default TopNavBar;
