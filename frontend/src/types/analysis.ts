
export interface InvasiveSpecies {
  nome: string;
  risco: 'Alto' | 'Médio' | 'Baixo';
  descricao: string;
}

export interface AnalysisResult {
  riscoDengue: 'Alto' | 'Médio' | 'Baixo' | 'N/A';
  especiesInvasoras: InvasiveSpecies[];
  viabilidadeRestauracao: 'Alta' | 'Média' | 'Baixa';
  planoRecuperacao: string[];
  resumoEcossistema: string;
}

export interface ProjectHistoryItem {
  id: string;
  fileName: string;
  date: string;
  thumbnail: string;
  result: AnalysisResult;
}
