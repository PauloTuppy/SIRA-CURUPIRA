
import React from 'react';
import { DashboardIcon, HistoryIcon, MapIcon } from './icons';

const Sidebar: React.FC = () => {
  const navItems = [
    { name: 'Dashboard', icon: DashboardIcon, active: true },
    { name: 'Mapa Interativo', icon: MapIcon, active: false },
    { name: 'Histórico', icon: HistoryIcon, active: false },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-gray-300 flex flex-col fixed h-full">
      <div className="flex-grow">
        <nav className="mt-5 px-2 space-y-2">
          {navItems.map((item) => (
            <a
              key={item.name}
              href="#"
              className={`
                ${item.active ? 'bg-slate-800 text-white' : 'hover:bg-slate-700 hover:text-white'}
                group flex items-center px-3 py-3 text-sm font-medium rounded-md transition-colors duration-200
              `}
            >
              <item.icon className="mr-3 h-6 w-6" />
              {item.name}
            </a>
          ))}
        </nav>
      </div>
       <div className="p-4 border-t border-slate-700">
          <p className="text-xs text-slate-500">© 2024 SIRA. Todos os direitos reservados.</p>
      </div>
    </aside>
  );
};

export default Sidebar;
