/**
 * Health Check Routes for SIRA RAG Service
 */

import { Router, Request, Response } from "express";
import * as admin from "firebase-admin";
import { config } from "../config/environment";
import { logger } from "../utils/logger";
import { asyncHandler } from "../utils/error-handler";
import { GBIFClient } from "../data-sources/gbif-client";
import { IUCNClient } from "../data-sources/iucn-client";
import { OBISClient } from "../data-sources/obis-client";
import { EBirdClient } from "../data-sources/ebird-client";

const router = Router();

// Initialize data source clients for health checks
const gbifClient = new GBIFClient();
const iucnClient = new IUCNClient();
const obisClient = new OBISClient();
const ebirdClient = new EBirdClient();

// Health check response interface
interface HealthCheckResponse {
  status: "healthy" | "unhealthy";
  timestamp: string;
  uptime: number;
  version: string;
  environment: string;
  services: {
    [key: string]: {
      status: "healthy" | "unhealthy";
      responseTime?: number;
      error?: string;
    };
  };
}

// Check Firestore connection
const checkFirestore = async (): Promise<{ status: "healthy" | "unhealthy"; responseTime?: number; error?: string }> => {
  const startTime = Date.now();
  
  try {
    const db = admin.firestore();
    await db.collection("health_check").limit(1).get();
    
    return {
      status: "healthy",
      responseTime: Date.now() - startTime,
    };
  } catch (error) {
    logger.error("Firestore health check failed", error);
    return {
      status: "unhealthy",
      responseTime: Date.now() - startTime,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
};

// Check Vertex AI connection
const checkVertexAI = async (): Promise<{ status: "healthy" | "unhealthy"; responseTime?: number; error?: string }> => {
  const startTime = Date.now();
  
  try {
    // Simple check - we'll implement actual Vertex AI ping later
    // For now, just check if credentials are available
    if (!config.vertexAI.projectId || !config.vertexAI.location) {
      throw new Error("Vertex AI configuration missing");
    }
    
    return {
      status: "healthy",
      responseTime: Date.now() - startTime,
    };
  } catch (error) {
    logger.error("Vertex AI health check failed", error);
    return {
      status: "unhealthy",
      responseTime: Date.now() - startTime,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
};

// Check Gemini API connection
const checkGemini = async (): Promise<{ status: "healthy" | "unhealthy"; responseTime?: number; error?: string }> => {
  const startTime = Date.now();
  
  try {
    if (!config.gemini.apiKey) {
      throw new Error("Gemini API key not configured");
    }
    
    // We'll implement actual API ping later
    return {
      status: "healthy",
      responseTime: Date.now() - startTime,
    };
  } catch (error) {
    logger.error("Gemini health check failed", error);
    return {
      status: "unhealthy",
      responseTime: Date.now() - startTime,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
};

// Basic health check
router.get("/", asyncHandler(async (req: Request, res: Response) => {
  const response: HealthCheckResponse = {
    status: "healthy",
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: config.app.version,
    environment: config.app.environment,
    services: {},
  };

  res.json(response);
}));

// Detailed health check
router.get("/detailed", asyncHandler(async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  // Run all health checks in parallel
  const [firestoreHealth, vertexAIHealth, geminiHealth, gbifHealth, iucnHealth, obisHealth, ebirdHealth] = await Promise.all([
    checkFirestore(),
    checkVertexAI(),
    checkGemini(),
    checkGBIF(),
    checkIUCN(),
    checkOBIS(),
    checkEBird(),
  ]);

  const services = {
    firestore: firestoreHealth,
    vertexai: vertexAIHealth,
    gemini: geminiHealth,
    gbif: gbifHealth,
    iucn: iucnHealth,
    obis: obisHealth,
    ebird: ebirdHealth,
  };

  // Determine overall status
  const overallStatus = Object.values(services).every(service => service.status === "healthy") 
    ? "healthy" 
    : "unhealthy";

  const response: HealthCheckResponse = {
    status: overallStatus,
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: config.app.version,
    environment: config.app.environment,
    services,
  };

  // Set appropriate status code
  const statusCode = overallStatus === "healthy" ? 200 : 503;
  
  // Log health check
  logger.info("Health check completed", {
    status: overallStatus,
    duration: Date.now() - startTime,
    services: Object.keys(services).reduce((acc, key) => {
      acc[key] = (services as any)[key].status;
      return acc;
    }, {} as Record<string, string>),
  });

  res.status(statusCode).json(response);
}));

// Readiness probe (for Kubernetes/Cloud Run)
router.get("/ready", asyncHandler(async (req: Request, res: Response) => {
  // Check if essential services are ready
  const firestoreHealth = await checkFirestore();
  
  if (firestoreHealth.status === "healthy") {
    res.json({
      status: "ready",
      timestamp: new Date().toISOString(),
    });
  } else {
    res.status(503).json({
      status: "not ready",
      timestamp: new Date().toISOString(),
      reason: "Firestore not available",
    });
  }
}));

// Liveness probe (for Kubernetes/Cloud Run)
router.get("/live", asyncHandler(async (req: Request, res: Response) => {
  // Simple liveness check
  res.json({
    status: "alive",
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
}));

// Metrics endpoint (basic)
router.get("/metrics", asyncHandler(async (req: Request, res: Response) => {
  const memoryUsage = process.memoryUsage();
  
  res.json({
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: {
      rss: memoryUsage.rss,
      heapTotal: memoryUsage.heapTotal,
      heapUsed: memoryUsage.heapUsed,
      external: memoryUsage.external,
    },
    cpu: process.cpuUsage(),
    version: config.app.version,
    environment: config.app.environment,
  });
}));

// Data source health checks
async function checkGBIF(): Promise<{ status: "healthy" | "unhealthy"; responseTime?: number; error?: string }> {
  try {
    return await gbifClient.healthCheck();
  } catch (error) {
    logger.error("GBIF health check failed", error);
    return {
      status: "unhealthy",
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function checkIUCN(): Promise<{ status: "healthy" | "unhealthy"; responseTime?: number; error?: string }> {
  try {
    return await iucnClient.healthCheck();
  } catch (error) {
    logger.error("IUCN health check failed", error);
    return {
      status: "unhealthy",
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function checkOBIS(): Promise<{ status: "healthy" | "unhealthy"; responseTime?: number; error?: string }> {
  try {
    return await obisClient.healthCheck();
  } catch (error) {
    logger.error("OBIS health check failed", error);
    return {
      status: "unhealthy",
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function checkEBird(): Promise<{ status: "healthy" | "unhealthy"; responseTime?: number; error?: string }> {
  try {
    return await ebirdClient.healthCheck();
  } catch (error) {
    logger.error("eBird health check failed", error);
    return {
      status: "unhealthy",
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

export { router as healthRoutes };
