/**
 * SIRA RAG Service - Main Entry Point
 * Retrieval Augmented Generation with Genkit and Firebase
 */

import { configureGenkit } from "@genkit-ai/core";
import { firebase } from "@genkit-ai/firebase";
import { googleAI } from "@genkit-ai/googleai";
import { vertexAI } from "@genkit-ai/vertexai";
import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import compression from "compression";

import { config } from "./config/environment";
import { logger } from "./utils/logger";
import { errorHandler } from "./utils/error-handler";
import { healthRoutes } from "./routes/health-routes";
import { ragRoutes } from "./routes/rag-routes";
import { ingestionRoutes } from "./routes/ingestion-routes";
import { initializeServices } from "./services/initialization";

// Initialize Firebase Admin
if (!admin.apps.length) {
  admin.initializeApp({
    projectId: config.firebase.projectId,
    storageBucket: config.firebase.storageBucket,
  });
}

// Initialize services
initializeServices().catch(error => {
  logger.error("Failed to initialize services", error);
  process.exit(1);
});

// Configure Genkit
configureGenkit({
  plugins: [
    firebase(),
    googleAI({
      apiKey: config.gemini.apiKey,
    }),
    vertexAI({
      projectId: config.firebase.projectId,
      location: config.vertexAI.location,
    }),
  ],
  logLevel: config.app.environment === "development" ? "debug" : "info",
  enableTracingAndMetrics: true,
});

// Create Express app
const app = express();

// Middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
}));

app.use(compression());
app.use(cors({
  origin: config.cors.origins,
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization", "X-Requested-With"],
}));

app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));

// Request logging
app.use((req, res, next) => {
  logger.info("Incoming request", {
    method: req.method,
    url: req.url,
    userAgent: req.get("User-Agent"),
    ip: req.ip,
  });
  next();
});

// Routes
app.use("/health", healthRoutes);
app.use("/api/v1/rag", ragRoutes);
app.use("/api/v1/ingestion", ingestionRoutes);

// Root endpoint
app.get("/", (req, res) => {
  res.json({
    service: "SIRA RAG Service",
    version: "1.0.0",
    status: "running",
    timestamp: new Date().toISOString(),
    environment: config.app.environment,
  });
});

// Error handling
app.use(errorHandler);

// 404 handler
app.use("*", (req, res) => {
  res.status(404).json({
    error: "Not Found",
    message: `Route ${req.originalUrl} not found`,
    timestamp: new Date().toISOString(),
  });
});

// Initialize services
initializeServices()
  .then(() => {
    logger.info("RAG Service initialized successfully");
  })
  .catch((error) => {
    logger.error("Failed to initialize RAG Service", { error });
    process.exit(1);
  });

// Export Firebase Functions
export const ragService = functions
  .region(config.firebase.region)
  .runWith({
    timeoutSeconds: 540,
    memory: "2GB" as const,
    maxInstances: 10,
  })
  .https
  .onRequest(app);

// Export for local development
export { app };

// Graceful shutdown
process.on("SIGTERM", () => {
  logger.info("SIGTERM received, shutting down gracefully");
  process.exit(0);
});

process.on("SIGINT", () => {
  logger.info("SIGINT received, shutting down gracefully");
  process.exit(0);
});

process.on("unhandledRejection", (reason, promise) => {
  logger.error("Unhandled Rejection at:", { promise, reason });
});

process.on("uncaughtException", (error) => {
  logger.error("Uncaught Exception:", { error });
  process.exit(1);
});
