
import React, { useState, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import FileUpload from './components/FileUpload';
import MapPlaceholder from './components/MapPlaceholder';
import ResultCard from './components/ResultCard';
import { AnalysisResult, ProjectHistoryItem } from './types';
import { analyzeEcosystemImage } from './services/geminiService';
import { AlertTriangleIcon, CheckCircleIcon, HistoryIcon, InfoIcon, LeafIcon } from './components/icons';

const App: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ProjectHistoryItem[]>([]);

  const resetState = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setAnalysisResult(null);
    setError(null);
    setIsLoading(false);
  };

  const getRiskColor = (risk: 'Alto' | 'Médio' | 'Baixo' | 'Alta' | 'Média' | 'N/A') => {
    switch (risk) {
      case 'Alto': return 'text-red-500';
      case 'Média':
      case 'Médio': return 'text-yellow-500';
      case 'Baixo':
      case 'Alta': return 'text-green-500';
      default: return 'text-gray-500';
    }
  };

  const handleFileSelect = useCallback(async (file: File) => {
    resetState();
    setSelectedFile(file);
    setIsLoading(true);

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64String = (reader.result as string).split(',')[1];
      setPreviewUrl(URL.createObjectURL(file));
      
      try {
        const result = await analyzeEcosystemImage(base64String, file.type);
        setAnalysisResult(result);

        const newHistoryItem: ProjectHistoryItem = {
          id: new Date().toISOString(),
          fileName: file.name,
          date: new Date().toLocaleDateString('pt-BR'),
          thumbnail: URL.createObjectURL(file),
          result,
        };
        setHistory(prev => [newHistoryItem, ...prev]);

      } catch (err) {
        if (err instanceof Error) {
            setError(err.message);
        } else {
            setError("Ocorreu um erro desconhecido.");
        }
      } finally {
        setIsLoading(false);
      }
    };
    reader.readAsDataURL(file);
  }, []);

  const WelcomeScreen = () => (
    <div className="text-center p-8 bg-white rounded-lg shadow-md">
      <LeafIcon className="w-16 h-16 mx-auto text-brand-secondary" />
      <h2 className="mt-4 text-2xl font-bold text-brand-primary">Bem-vindo ao SIRA</h2>
      <p className="mt-2 text-gray-600">
        Para começar, faça o upload de uma imagem ou vídeo de um ecossistema.
      </p>
    </div>
  );

  const LoadingScreen = () => (
    <div className="text-center p-8 bg-white rounded-lg shadow-md">
        <div className="flex justify-center items-center">
            <svg className="animate-spin h-12 w-12 text-brand-secondary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
        </div>
      <h2 className="mt-4 text-xl font-semibold text-brand-primary animate-pulse-fast">Analisando ecossistema...</h2>
      <p className="mt-2 text-sm text-gray-500">A IA está processando a imagem. Isso pode levar alguns instantes.</p>
    </div>
  );

  const ErrorScreen = () => (
    <div className="text-center p-8 bg-red-50 border border-red-200 rounded-lg shadow-md">
      <AlertTriangleIcon className="w-16 h-16 mx-auto text-red-500" />
      <h2 className="mt-4 text-2xl font-bold text-red-700">Ocorreu um erro</h2>
      <p className="mt-2 text-red-600">{error}</p>
      <button onClick={resetState} className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition">
          Tentar Novamente
      </button>
    </div>
  );

  return (
    <div className="bg-gray-100 min-h-screen">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 ml-64 p-6 lg:p-8">
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            {/* Coluna de Análise e Resultados */}
            <div className="xl:col-span-2 space-y-8">
              {/* Seção de Upload */}
              <section className="bg-white p-6 rounded-xl shadow-sm">
                <h2 className="text-xl font-bold text-gray-800 mb-4">1. Iniciar Nova Análise</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <FileUpload onFileSelect={handleFileSelect} disabled={isLoading} />
                  <MapPlaceholder />
                </div>
              </section>

              {/* Seção de Resultados */}
              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-4">2. Resultados da Análise</h2>
                {isLoading ? <LoadingScreen/> : error ? <ErrorScreen /> : !analysisResult ? <WelcomeScreen /> : (
                  <div className="space-y-6">
                    {/* Preview e Resumo */}
                    <div className="bg-white p-6 rounded-xl shadow-sm grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="md:col-span-1">
                        {previewUrl && <img src={previewUrl} alt="Preview" className="rounded-lg object-cover w-full h-48" />}
                      </div>
                      <div className="md:col-span-2">
                          <h3 className="text-lg font-semibold text-gray-900">Resumo do Ecossistema</h3>
                          <p className="text-gray-600 text-sm mt-2">{analysisResult.resumoEcossistema}</p>
                      </div>
                    </div>

                    {/* Cards de Métricas */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        <ResultCard title="Risco de Dengue" value={analysisResult.riscoDengue} icon={<AlertTriangleIcon className="h-6 w-6 text-red-800"/>} colorClass="bg-red-200" description="Baseado em focos de água parada" />
                        <ResultCard title="Espécies Invasoras" value={`${analysisResult.especiesInvasoras.length} detectada(s)`} icon={<InfoIcon className="h-6 w-6 text-yellow-800"/>} colorClass="bg-yellow-200" description="Ameaças à biodiversidade local" />
                        <ResultCard title="Viabilidade de Restauração" value={analysisResult.viabilidadeRestauracao} icon={<CheckCircleIcon className="h-6 w-6 text-green-800"/>} colorClass="bg-green-200" description="Potencial de recuperação da área" />
                    </div>
                    
                    {/* Detalhes */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* Espécies Invasoras */}
                      <div className="bg-white p-6 rounded-xl shadow-sm">
                        <h3 className="text-lg font-semibold text-gray-900 mb-3">Detalhes: Espécies Invasoras</h3>
                        <div className="space-y-4 max-h-60 overflow-y-auto pr-2">
                           {analysisResult.especiesInvasoras.length > 0 ? analysisResult.especiesInvasoras.map((s, i) => (
                             <div key={i} className="border-l-4 p-3 rounded-r-md bg-gray-50" style={{borderColor: getRiskColor(s.risco).replace('text-','').replace('-500','')}}>
                                 <div className="flex justify-between items-center">
                                      <p className="font-bold text-gray-800">{s.nome}</p>
                                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getRiskColor(s.risco)} bg-opacity-20`}>{s.risco}</span>
                                 </div>
                               <p className="text-sm text-gray-600 mt-1">{s.descricao}</p>
                             </div>
                           )) : <p className="text-sm text-gray-500">Nenhuma espécie invasora proeminente foi detectada na imagem.</p>}
                        </div>
                      </div>
                      {/* Plano de Recuperação */}
                      <div className="bg-white p-6 rounded-xl shadow-sm">
                         <h3 className="text-lg font-semibold text-gray-900 mb-3">Plano de Recuperação Sugerido</h3>
                         <ul className="space-y-3">
                           {analysisResult.planoRecuperacao.map((step, i) => (
                              <li key={i} className="flex items-start">
                                  <CheckCircleIcon className="h-5 w-5 text-brand-secondary mr-3 mt-0.5 flex-shrink-0"/>
                                  <span className="text-sm text-gray-700">{step}</span>
                              </li>
                           ))}
                         </ul>
                      </div>
                    </div>

                  </div>
                )}
              </section>
            </div>
            {/* Coluna do Histórico */}
            <aside className="xl:col-span-1 bg-white p-6 rounded-xl shadow-sm">
                <div className="flex items-center mb-4">
                  <HistoryIcon className="h-6 w-6 text-gray-700 mr-3"/>
                  <h2 className="text-xl font-bold text-gray-800">Histórico de Análises</h2>
                </div>
                <div className="space-y-4 max-h-[calc(100vh-15rem)] overflow-y-auto">
                    {history.length > 0 ? history.map(item => (
                         <div key={item.id} className="flex items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition cursor-pointer" onClick={() => { setAnalysisResult(item.result); setPreviewUrl(item.thumbnail);}}>
                             <img src={item.thumbnail} alt={item.fileName} className="w-16 h-16 rounded-md object-cover flex-shrink-0" />
                             <div className="ml-4 truncate">
                                 <p className="text-sm font-semibold text-gray-800 truncate" title={item.fileName}>{item.fileName}</p>
                                 <p className="text-xs text-gray-500">{item.date}</p>
                                 <p className={`text-xs font-medium ${getRiskColor(item.result.viabilidadeRestauracao)}`}>Viabilidade: {item.result.viabilidadeRestauracao}</p>
                             </div>
                         </div>
                    )) : (
                        <div className="text-center py-10 px-4">
                            <HistoryIcon className="h-10 w-10 text-gray-300 mx-auto"/>
                            <p className="mt-2 text-sm text-gray-500">Nenhuma análise foi realizada ainda.</p>
                            <p className="text-xs text-gray-400">Seu histórico aparecerá aqui.</p>
                        </div>
                    )}
                </div>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;
