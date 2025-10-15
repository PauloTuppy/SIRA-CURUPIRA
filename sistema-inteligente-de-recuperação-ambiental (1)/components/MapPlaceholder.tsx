
import React from 'react';
import { MapIcon } from './icons';

const MapPlaceholder: React.FC = () => {
  return (
    <div className="relative h-64 w-full bg-gray-300 rounded-lg overflow-hidden border border-gray-300 flex items-center justify-center">
      <img 
        src="https://picsum.photos/seed/map/800/400" 
        alt="Mapa da área" 
        className="w-full h-full object-cover opacity-50" 
      />
      <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center text-white p-4">
        <MapIcon className="h-12 w-12 mb-2" />
        <h3 className="text-lg font-bold">Mapa Interativo</h3>
        <p className="text-sm text-center">
          Em breve: selecione a área de análise diretamente no mapa.
        </p>
      </div>
    </div>
  );
};

export default MapPlaceholder;
