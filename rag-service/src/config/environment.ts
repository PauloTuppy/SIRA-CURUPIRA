/**
 * Environment Configuration for SIRA RAG Service
 */

import * as dotenv from "dotenv";

// Load environment variables
dotenv.config();

export interface Config {
  app: {
    name: string;
    version: string;
    environment: string;
    port: number;
    debug: boolean;
  };
  firebase: {
    projectId: string;
    region: string;
    storageBucket: string;
    databaseURL?: string;
  };
  firestore: {
    database: string;
    collections: {
      knowledgeBase: string;
      embeddings: string;
      analyses: string;
      ingestionJobs: string;
    };
  };
  gemini: {
    apiKey: string;
    model: string;
    safetySettings: any[];
  };
  vertexAI: {
    projectId: string;
    location: string;
    embeddingModel: string;
    dimensions: number;
  };
  dataSources: {
    gbif: {
      apiUrl: string;
      timeout: number;
    };
    iucn: {
      apiUrl: string;
      apiToken: string;
      timeout: number;
    };
    obis: {
      apiUrl: string;
      timeout: number;
    };
    ebird: {
      apiUrl: string;
      apiKey: string;
      timeout: number;
    };
  };
  rag: {
    embeddingModel: string;
    vectorDimension: number;
    similarityThreshold: number;
    maxRetrievalResults: number;
    chunkSize: number;
    chunkOverlap: number;
  };
  cors: {
    origins: string[];
  };
  rateLimit: {
    windowMs: number;
    maxRequests: number;
  };
  cache: {
    ttl: number;
    maxSize: number;
  };
  monitoring: {
    enabled: boolean;
    metricsPort: number;
  };
}

export const config: Config = {
  app: {
    name: process.env.APP_NAME || "SIRA RAG Service",
    version: process.env.APP_VERSION || "1.0.0",
    environment: process.env.ENVIRONMENT || "development",
    port: parseInt(process.env.PORT || "8001", 10),
    debug: process.env.DEBUG === "true",
  },
  firebase: {
    projectId: process.env.GOOGLE_CLOUD_PROJECT || process.env.FIREBASE_PROJECT_ID || "ecosystem-recovery-ai",
    region: process.env.FIREBASE_REGION || "us-central1",
    storageBucket: process.env.FIREBASE_STORAGE_BUCKET || "ecosystem-recovery-ai.appspot.com",
    databaseURL: process.env.FIREBASE_DATABASE_URL,
  },
  firestore: {
    database: process.env.FIRESTORE_DATABASE || "(default)",
    collections: {
      knowledgeBase: process.env.FIRESTORE_COLLECTION_KNOWLEDGE_BASE || "knowledge_base",
      embeddings: process.env.FIRESTORE_COLLECTION_EMBEDDINGS || "embeddings",
      analyses: process.env.FIRESTORE_COLLECTION_ANALYSES || "analyses",
      ingestionJobs: process.env.FIRESTORE_COLLECTION_INGESTION_JOBS || "ingestion_jobs",
    },
  },
  gemini: {
    apiKey: process.env.GEMINI_API_KEY || "",
    model: process.env.GEMINI_MODEL || "gemini-1.5-pro",
    safetySettings: [
      {
        category: "HARM_CATEGORY_HARASSMENT",
        threshold: "BLOCK_NONE",
      },
      {
        category: "HARM_CATEGORY_HATE_SPEECH",
        threshold: "BLOCK_NONE",
      },
      {
        category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold: "BLOCK_NONE",
      },
      {
        category: "HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold: "BLOCK_NONE",
      },
    ],
  },
  vertexAI: {
    projectId: process.env.GOOGLE_CLOUD_PROJECT || "ecosystem-recovery-ai",
    location: process.env.VERTEX_AI_LOCATION || "us-central1",
    embeddingModel: process.env.EMBEDDING_MODEL || "text-embedding-004",
    dimensions: parseInt(process.env.VECTOR_DIMENSION || "768", 10),
  },
  dataSources: {
    gbif: {
      apiUrl: process.env.GBIF_API_URL || "https://api.gbif.org/v1",
      timeout: parseInt(process.env.GBIF_TIMEOUT || "30000", 10),
    },
    iucn: {
      apiUrl: process.env.IUCN_API_URL || "https://apiv3.iucnredlist.org/api/v3",
      apiToken: process.env.IUCN_API_TOKEN || "",
      timeout: parseInt(process.env.IUCN_TIMEOUT || "30000", 10),
    },
    obis: {
      apiUrl: process.env.OBIS_API_URL || "https://api.obis.org",
      timeout: parseInt(process.env.OBIS_TIMEOUT || "30000", 10),
    },
    ebird: {
      apiUrl: process.env.EBIRD_API_URL || "https://api.ebird.org/v2",
      apiKey: process.env.EBIRD_API_KEY || "",
      timeout: parseInt(process.env.EBIRD_TIMEOUT || "30000", 10),
    },
  },
  rag: {
    embeddingModel: process.env.EMBEDDING_MODEL || "text-embedding-004",
    vectorDimension: parseInt(process.env.VECTOR_DIMENSION || "768", 10),
    similarityThreshold: parseFloat(process.env.SIMILARITY_THRESHOLD || "0.7"),
    maxRetrievalResults: parseInt(process.env.MAX_RETRIEVAL_RESULTS || "10", 10),
    chunkSize: parseInt(process.env.CHUNK_SIZE || "1000", 10),
    chunkOverlap: parseInt(process.env.CHUNK_OVERLAP || "200", 10),
  },
  cors: {
    origins: (process.env.CORS_ORIGINS || "http://localhost:5173,http://localhost:3000").split(","),
  },
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || "900000", 10), // 15 minutes
    maxRequests: parseInt(process.env.RATE_LIMIT_REQUESTS || "100", 10),
  },
  cache: {
    ttl: parseInt(process.env.CACHE_TTL_SECONDS || "3600", 10), // 1 hour
    maxSize: parseInt(process.env.CACHE_MAX_SIZE || "1000", 10),
  },
  monitoring: {
    enabled: process.env.ENABLE_MONITORING === "true",
    metricsPort: parseInt(process.env.METRICS_PORT || "9090", 10),
  },
};

// Validate required configuration
const requiredEnvVars = [
  "GEMINI_API_KEY",
  "GOOGLE_CLOUD_PROJECT",
];

const missingEnvVars = requiredEnvVars.filter(envVar => !process.env[envVar]);

if (missingEnvVars.length > 0) {
  throw new Error(`Missing required environment variables: ${missingEnvVars.join(", ")}`);
}
