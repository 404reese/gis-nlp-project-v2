import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="bg-[#faf5ee] dark:bg-stone-950 border-t border-stone-200/60 dark:border-stone-800 w-full mt-auto">
      <div className="flex justify-between items-center px-8 py-6 w-full max-w-7xl mx-auto">
        <p className="font-['Manrope'] text-xs text-stone-500">© 2024 Sahara Geospatial. All rights reserved.</p>
        <div className="flex gap-6 font-['Manrope'] text-xs text-stone-500">
          <Link to="#" className="text-[#c2652a] hover:text-stone-700 dark:hover:text-stone-200 underline opacity-80 hover:opacity-100 transition-opacity">
            Privacy Policy
          </Link>
          <Link to="#" className="text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 underline opacity-80 hover:opacity-100 transition-opacity">
            Terms of Service
          </Link>
          <Link to="#" className="text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 underline opacity-80 hover:opacity-100 transition-opacity">
            API Documentation
          </Link>
          <Link to="#" className="text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 underline opacity-80 hover:opacity-100 transition-opacity">
            Support
          </Link>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
