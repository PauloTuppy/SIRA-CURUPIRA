/**
 * RAG Routes for SIRA RAG Service
 * Placeholder implementation - will be expanded in next subtasks
 */

import { Router, Request, Response } from "express";
import { logger } from "../utils/logger";
import { asyncHandler } from "../utils/error-handler";
import { EmbeddingService } from "../services/embedding-service";
import { FirestoreService } from "../services/firestore-service";

const router = Router();
const embeddingService = new EmbeddingService();
const firestoreService = new FirestoreService();

// RAG query interface
interface RAGQueryRequest {
  query: string;
  context?: string;
  maxResults?: number;
  threshold?: number;
  sources?: string[];
}

interface RAGQueryResponse {
  query: string;
  results: Array<{
    content: string;
    source: string;
    score: number;
    metadata: any;
  }>;
  totalResults: number;
  processingTime: number;
  timestamp: string;
}

// Query RAG system
router.post("/query", asyncHandler(async (req: Request, res: Response): Promise<void> => {
  const startTime = Date.now();
  const { query, maxResults = 10, threshold = 0.7, sources }: RAGQueryRequest = req.body;

  // Validate request
  if (!query || typeof query !== "string" || query.trim().length === 0) {
    res.status(400).json({
      error: "Query is required and must be a non-empty string",
    });
    return;
  }

  logger.info("RAG query received", {
    query: query.substring(0, 100),
    maxResults,
    threshold,
    sources,
  });

  try {
    // Generate embedding for the query
    const queryEmbedding = await embeddingService.generateEmbedding({
      text: query,
      metadata: { type: "query" },
    });

    // Perform vector search
    const searchResults = await firestoreService.vectorSearch({
      embedding: queryEmbedding.embedding,
      limit: maxResults,
      threshold,
      filters: sources ? { source: sources } : undefined,
    });

    // Format response
    const response: RAGQueryResponse = {
      query,
      results: searchResults.results.map(result => ({
        content: result.content,
        source: result.metadata.source,
        score: result.score,
        metadata: {
          type: result.metadata.type,
          scientificName: result.metadata.scientificName,
          location: result.metadata.location,
          timestamp: result.metadata.timestamp.toDate().toISOString(),
        },
      })),
      totalResults: searchResults.totalResults,
      processingTime: Date.now() - startTime,
      timestamp: new Date().toISOString(),
    };

    res.json(response);

  } catch (error) {
    logger.error("RAG query failed", {
      query: query.substring(0, 100),
      error: error instanceof Error ? error.message : String(error),
    });

    res.status(500).json({
      error: "RAG query failed",
      message: error instanceof Error ? error.message : String(error),
    });
  }
}));

// Get embeddings for text
router.post("/embeddings", asyncHandler(async (req: Request, res: Response): Promise<void> => {
  const { text } = req.body;

  if (!text || typeof text !== "string") {
    res.status(400).json({
      error: "Text is required and must be a string",
    });
    return;
  }

  logger.info("Embedding request received", {
    textLength: text.length,
  });

  try {
    // Generate embedding using the service
    const embeddingResponse = await embeddingService.generateEmbedding({
      text,
      metadata: { type: "manual_request" },
    });

    const response = {
      text: text.substring(0, 100) + (text.length > 100 ? "..." : ""),
      embedding: embeddingResponse.embedding,
      model: embeddingResponse.model,
      dimensions: embeddingResponse.dimensions,
      processingTime: embeddingResponse.processingTime,
      timestamp: new Date().toISOString(),
    };

    res.json(response);

  } catch (error) {
    logger.error("Embedding generation failed", {
      textLength: text.length,
      error: error instanceof Error ? error.message : String(error),
    });

    res.status(500).json({
      error: "Embedding generation failed",
      message: error instanceof Error ? error.message : String(error),
    });
  }
}));

// Search similar documents
router.post("/search", asyncHandler(async (req: Request, res: Response): Promise<void> => {
  const { embedding, maxResults = 10, threshold = 0.7 } = req.body;

  if (!embedding || !Array.isArray(embedding)) {
    res.status(400).json({
      error: "Embedding is required and must be an array",
    });
    return;
  }

  logger.info("Vector search request received", {
    embeddingDimension: embedding.length,
    maxResults,
    threshold,
  });

  try {
    const startTime = Date.now();

    // Perform vector search using the service
    const searchResults = await firestoreService.vectorSearch({
      embedding,
      limit: maxResults,
      threshold,
    });

    const response = {
      results: searchResults.results.map(result => ({
        id: result.id,
        content: result.content,
        score: result.score,
        metadata: {
          source: result.metadata.source,
          type: result.metadata.type,
          scientificName: result.metadata.scientificName,
          location: result.metadata.location,
        },
      })),
      totalResults: searchResults.totalResults,
      processingTime: Date.now() - startTime,
      timestamp: new Date().toISOString(),
    };

    res.json(response);

  } catch (error) {
    logger.error("Vector search failed", {
      embeddingDimension: embedding.length,
      error: error instanceof Error ? error.message : String(error),
    });

    res.status(500).json({
      error: "Vector search failed",
      message: error instanceof Error ? error.message : String(error),
    });
  }
}));

// Get knowledge base statistics
router.get("/stats", asyncHandler(async (req: Request, res: Response) => {
  logger.info("Knowledge base stats requested");

  try {
    // Get statistics from Firestore service
    const stats = await firestoreService.getStatistics();

    const response = {
      totalDocuments: stats.totalDocuments,
      totalEmbeddings: stats.totalEmbeddings,
      sources: {
        gbif: stats.sourceBreakdown.gbif || 0,
        iucn: stats.sourceBreakdown.iucn || 0,
        obis: stats.sourceBreakdown.obis || 0,
        ebird: stats.sourceBreakdown.ebird || 0,
      },
      types: stats.typeBreakdown,
      lastUpdated: new Date().toISOString(),
      status: "active",
    };

    res.json(response);

  } catch (error) {
    logger.error("Failed to get knowledge base stats", {
      error: error instanceof Error ? error.message : String(error),
    });

    res.status(500).json({
      error: "Failed to get knowledge base stats",
      message: error instanceof Error ? error.message : String(error),
    });
  }
}));

export { router as ragRoutes };
