
import { GoogleGenAI, Type } from "@google/genai";
import { AnalysisResult } from '../types';

const fileToGenerativePart = (base64: string, mimeType: string) => {
  return {
    inlineData: {
      data: base64,
      mimeType,
    },
  };
};

export const analyzeEcosystemImage = async (
  base64Image: string,
  mimeType: string
): Promise<AnalysisResult> => {
    
  if (!process.env.API_KEY) {
    console.error("API_KEY do Gemini não configurada.");
    throw new Error("A chave da API não foi configurada. Verifique as variáveis de ambiente.");
  }
  
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

  const imagePart = fileToGenerativePart(base64Image, mimeType);
  const prompt = `
    Você é um especialista em ecologia e recuperação ambiental. Analise a imagem fornecida de um ecossistema, que pode ser do Brasil ou de outro lugar.
    Sua tarefa é fornecer uma análise detalhada em português do Brasil, estruturada exatamente como o esquema JSON a seguir.
    
    Análise da Imagem:
    1.  **Resumo do Ecossistema**: Descreva brevemente o tipo de ecossistema que você vê (floresta, área urbana, corpo d'água, etc.) e sua condição geral.
    2.  **Identificação de Espécies Invasoras**: Identifique até 3 espécies invasoras notáveis (fauna ou flora) na imagem. Para cada uma, forneça o nome, nível de risco (Alto, Médio, Baixo) e uma breve descrição do impacto. Se nenhuma for visível, retorne uma lista vazia. Exemplos comuns no Brasil incluem Aedes aegypti (foco de dengue em água parada), caramujos africanos, e a planta aquática baronesa (Eichhornia crassipes).
    3.  **Risco de Dengue**: Com base na presença de água parada ou outros fatores visíveis, avalie o risco de proliferação do Aedes aegypti (Alto, Médio, Baixo ou N/A).
    4.  **Viabilidade de Restauração**: Avalie a viabilidade de um projeto de restauração ecológica para esta área (Alta, Média, Baixa) com base na degradação observada.
    5.  **Plano de Recuperação**: Gere uma lista de 3 a 5 ações recomendadas para um plano de recuperação ambiental, começando com as mais urgentes.
  `;

  try {
    const result = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: { parts: [imagePart, { text: prompt }] },
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            resumoEcossistema: { type: Type.STRING, description: "Breve resumo sobre o ecossistema e sua condição." },
            riscoDengue: { type: Type.STRING, enum: ['Alto', 'Médio', 'Baixo', 'N/A'], description: "Risco de proliferação do Aedes aegypti." },
            especiesInvasoras: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  nome: { type: Type.STRING },
                  risco: { type: Type.STRING, enum: ['Alto', 'Médio', 'Baixo'] },
                  descricao: { type: Type.STRING },
                },
                required: ['nome', 'risco', 'descricao']
              },
            },
            viabilidadeRestauracao: { type: Type.STRING, enum: ['Alta', 'Média', 'Baixa'], description: "Viabilidade de restauração da área." },
            planoRecuperacao: { type: Type.ARRAY, items: { type: Type.STRING }, description: "Lista de ações para recuperação." },
          },
          required: ['resumoEcossistema', 'riscoDengue', 'especiesInvasoras', 'viabilidadeRestauracao', 'planoRecuperacao']
        },
      },
    });

    const responseJson = JSON.parse(result.text);
    return responseJson as AnalysisResult;

  } catch (error) {
    console.error("Erro ao chamar a API Gemini:", error);
    throw new Error("Falha na análise da imagem. A IA não conseguiu processar a solicitação.");
  }
};
