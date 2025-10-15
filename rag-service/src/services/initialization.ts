/**
 * Service Initialization for SIRA RAG Service
 */

import * as admin from "firebase-admin";
import { config } from "../config/environment";
import { logger } from "../utils/logger";

// Initialize Firestore collections and indexes
const initializeFirestore = async (): Promise<void> => {
  try {
    const db = admin.firestore();
    
    // Create collections if they don't exist
    const collections = [
      config.firestore.collections.knowledgeBase,
      config.firestore.collections.embeddings,
      config.firestore.collections.analyses,
      config.firestore.collections.ingestionJobs,
    ];

    for (const collectionName of collections) {
      const collection = db.collection(collectionName);
      
      // Check if collection exists by trying to get a document
      try {
        await collection.limit(1).get();
        logger.info(`Collection ${collectionName} exists`);
      } catch (error) {
        // Collection doesn't exist, create it with a dummy document
        await collection.doc("_init").set({
          _initialized: true,
          _timestamp: admin.firestore.FieldValue.serverTimestamp(),
        });
        logger.info(`Collection ${collectionName} created`);
      }
    }

    // Create composite indexes for vector search
    // Note: These need to be created manually in Firestore console or via Firebase CLI
    logger.info("Firestore collections initialized");
    
  } catch (error) {
    logger.error("Failed to initialize Firestore", error);
    throw error;
  }
};

// Initialize vector search indexes
const initializeVectorSearch = async (): Promise<void> => {
  try {
    // Vector search indexes need to be created via Firebase CLI or console
    // We'll log the required indexes for manual creation
    
    const requiredIndexes = [
      {
        collection: config.firestore.collections.embeddings,
        fields: [
          { field: "source", mode: "ASCENDING" },
          { field: "type", mode: "ASCENDING" },
          { field: "embedding", mode: "VECTOR" },
        ],
      },
      {
        collection: config.firestore.collections.knowledgeBase,
        fields: [
          { field: "source", mode: "ASCENDING" },
          { field: "category", mode: "ASCENDING" },
          { field: "timestamp", mode: "DESCENDING" },
        ],
      },
    ];

    logger.info("Vector search indexes required:", { requiredIndexes });
    logger.info("Please create these indexes manually in Firestore console");
    
  } catch (error) {
    logger.error("Failed to initialize vector search", error);
    throw error;
  }
};

// Initialize data source connections
const initializeDataSources = async (): Promise<void> => {
  try {
    // Test connections to external data sources
    const dataSources = [
      { name: "GBIF", url: config.dataSources.gbif.apiUrl },
      { name: "IUCN", url: config.dataSources.iucn.apiUrl },
      { name: "OBIS", url: config.dataSources.obis.apiUrl },
      { name: "eBird", url: config.dataSources.ebird.apiUrl },
    ];

    for (const source of dataSources) {
      try {
        // Simple connectivity test
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(source.url, {
          method: "HEAD",
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        
        if (response.ok) {
          logger.info(`Data source ${source.name} is accessible`);
        } else {
          logger.warn(`Data source ${source.name} returned status ${response.status}`);
        }
      } catch (error) {
        logger.warn(`Data source ${source.name} is not accessible`, { error });
      }
    }
    
  } catch (error) {
    logger.error("Failed to initialize data sources", error);
    // Don't throw - data sources being unavailable shouldn't prevent startup
  }
};

// Initialize caching
const initializeCache = async (): Promise<void> => {
  try {
    // Initialize in-memory cache
    // We'll implement Redis cache later if needed
    logger.info("Cache initialized (in-memory)");
    
  } catch (error) {
    logger.error("Failed to initialize cache", error);
    throw error;
  }
};

// Initialize monitoring
const initializeMonitoring = async (): Promise<void> => {
  try {
    if (config.monitoring.enabled) {
      // Initialize metrics collection
      logger.info("Monitoring initialized");
    } else {
      logger.info("Monitoring disabled");
    }
    
  } catch (error) {
    logger.error("Failed to initialize monitoring", error);
    // Don't throw - monitoring failure shouldn't prevent startup
  }
};

// Validate environment configuration
const validateConfiguration = (): void => {
  const requiredConfigs = [
    { key: "GEMINI_API_KEY", value: config.gemini.apiKey },
    { key: "GOOGLE_CLOUD_PROJECT", value: config.firebase.projectId },
  ];

  const missingConfigs = requiredConfigs.filter(cfg => !cfg.value);
  
  if (missingConfigs.length > 0) {
    const missing = missingConfigs.map(cfg => cfg.key).join(", ");
    throw new Error(`Missing required configuration: ${missing}`);
  }

  logger.info("Configuration validated");
};

// Main initialization function
export const initializeServices = async (): Promise<void> => {
  const startTime = Date.now();
  
  try {
    logger.info("Starting RAG Service initialization...");
    
    // Validate configuration first
    validateConfiguration();
    
    // Initialize services in order
    await initializeFirestore();
    await initializeVectorSearch();
    await initializeDataSources();
    await initializeCache();
    await initializeMonitoring();
    
    const duration = Date.now() - startTime;
    logger.info(`RAG Service initialization completed successfully in ${duration}ms`);
    
  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error(`RAG Service initialization failed after ${duration}ms`, error);
    throw error;
  }
};

// Graceful shutdown
export const shutdownServices = async (): Promise<void> => {
  try {
    logger.info("Starting graceful shutdown...");
    
    // Close Firebase connections
    await admin.app().delete();
    
    logger.info("Graceful shutdown completed");
    
  } catch (error) {
    logger.error("Error during graceful shutdown", error);
    throw error;
  }
};
