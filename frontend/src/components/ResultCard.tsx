
import React from 'react';

interface ResultCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  colorClass: string;
  description?: string;
}

const ResultCard: React.FC<ResultCardProps> = ({ title, value, icon, colorClass, description }) => {
  return (
    <div className="bg-white p-5 rounded-xl shadow-lg flex items-start space-x-4 transition-transform duration-300 hover:scale-105">
      <div className={`p-3 rounded-full ${colorClass}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-800">{value}</p>
        {description && <p className="text-xs text-gray-400 mt-1">{description}</p>}
      </div>
    </div>
  );
};

export default ResultCard;
