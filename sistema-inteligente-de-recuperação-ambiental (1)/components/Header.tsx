
import React from 'react';
import { LeafIcon } from './icons';

const Header: React.FC = () => {
  return (
    <header className="bg-brand-primary shadow-md text-white sticky top-0 z-30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <LeafIcon className="h-8 w-8 text-brand-accent" />
            <h1 className="ml-3 text-2xl font-bold tracking-tight">
              SIRA
              <span className="hidden sm:inline text-base font-normal ml-2 opacity-75">
                Sistema Inteligente de Recuperação Ambiental
              </span>
            </h1>
          </div>
          <div className="flex items-center">
            <button className="p-2 rounded-full hover:bg-brand-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-brand-primary focus:ring-white">
              <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </button>
            <img
              className="h-9 w-9 rounded-full ml-4"
              src="https://picsum.photos/100/100"
              alt="Avatar do usuário"
            />
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
