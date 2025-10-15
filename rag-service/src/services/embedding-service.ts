/**
 * Embedding Service using Vertex AI
 */

import { embed } from "@genkit-ai/ai/embedder";
import { textEmbedding004 } from "@genkit-ai/vertexai";
import { config } from "../config/environment";
import { logger, logPerformance } from "../utils/logger";
import { RAGError } from "../utils/error-handler";

export interface EmbeddingRequest {
  text: string;
  metadata?: Record<string, any>;
}

export interface EmbeddingResponse {
  embedding: number[];
  text: string;
  model: string;
  dimensions: number;
  metadata?: Record<string, any>;
  processingTime: number;
}

export interface BatchEmbeddingRequest {
  texts: string[];
  batchSize?: number;
  metadata?: Record<string, any>;
}

export interface BatchEmbeddingResponse {
  embeddings: EmbeddingResponse[];
  totalTexts: number;
  successCount: number;
  errorCount: number;
  totalProcessingTime: number;
  averageProcessingTime: number;
}

export class EmbeddingService {
  private model: string;
  private dimensions: number;
  private maxTextLength: number;
  private batchSize: number;

  constructor() {
    this.model = config.rag.embeddingModel;
    this.dimensions = config.rag.vectorDimension;
    this.maxTextLength = 8192; // Vertex AI text-embedding-004 limit
    this.batchSize = 100; // Reasonable batch size for API limits
  }

  /**
   * Generate embedding for a single text
   */
  async generateEmbedding(request: EmbeddingRequest): Promise<EmbeddingResponse> {
    const startTime = Date.now();
    
    try {
      // Validate input
      if (!request.text || typeof request.text !== "string") {
        throw new RAGError("embedding", "Text is required and must be a string");
      }

      if (request.text.trim().length === 0) {
        throw new RAGError("embedding", "Text cannot be empty");
      }

      // Truncate text if too long
      let processedText = request.text;
      if (processedText.length > this.maxTextLength) {
        processedText = processedText.substring(0, this.maxTextLength);
        logger.warn("Text truncated for embedding", {
          originalLength: request.text.length,
          truncatedLength: processedText.length,
        });
      }

      // Generate embedding using Genkit
      const result = await embed({
        embedder: textEmbedding004,
        content: processedText,
      });

      const processingTime = Date.now() - startTime;

      logPerformance("embedding_generation", processingTime, {
        textLength: processedText.length,
        model: this.model,
        dimensions: this.dimensions,
      });

      return {
        embedding: result,
        text: processedText,
        model: this.model,
        dimensions: this.dimensions,
        metadata: request.metadata,
        processingTime,
      };

    } catch (error) {
      const processingTime = Date.now() - startTime;
      
      logger.error("Failed to generate embedding", {
        error: error instanceof Error ? error.message : String(error),
        textLength: request.text?.length,
        processingTime,
      });

      if (error instanceof RAGError) {
        throw error;
      }

      throw new RAGError(
        "embedding",
        `Failed to generate embedding: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Generate embeddings for multiple texts in batches
   */
  async generateBatchEmbeddings(request: BatchEmbeddingRequest): Promise<BatchEmbeddingResponse> {
    const startTime = Date.now();
    const batchSize = request.batchSize || this.batchSize;
    const embeddings: EmbeddingResponse[] = [];
    let successCount = 0;
    let errorCount = 0;

    try {
      logger.info("Starting batch embedding generation", {
        totalTexts: request.texts.length,
        batchSize,
      });

      // Process texts in batches
      for (let i = 0; i < request.texts.length; i += batchSize) {
        const batch = request.texts.slice(i, i + batchSize);
        const batchStartTime = Date.now();

        logger.info(`Processing batch ${Math.floor(i / batchSize) + 1}`, {
          batchStart: i,
          batchSize: batch.length,
        });

        // Process batch concurrently with controlled concurrency
        const batchPromises = batch.map(async (text, index) => {
          try {
            const embedding = await this.generateEmbedding({
              text,
              metadata: {
                ...request.metadata,
                batchIndex: Math.floor(i / batchSize),
                textIndex: i + index,
              },
            });
            successCount++;
            return embedding;
          } catch (error) {
            errorCount++;
            logger.error(`Failed to generate embedding for text ${i + index}`, {
              error: error instanceof Error ? error.message : String(error),
              textPreview: text.substring(0, 100),
            });
            return null;
          }
        });

        const batchResults = await Promise.all(batchPromises);
        
        // Add successful embeddings to results
        batchResults.forEach(result => {
          if (result) {
            embeddings.push(result);
          }
        });

        const batchTime = Date.now() - batchStartTime;
        logger.info(`Completed batch ${Math.floor(i / batchSize) + 1}`, {
          batchTime,
          successfulInBatch: batchResults.filter(r => r !== null).length,
          errorsInBatch: batchResults.filter(r => r === null).length,
        });

        // Add small delay between batches to respect rate limits
        if (i + batchSize < request.texts.length) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }

      const totalProcessingTime = Date.now() - startTime;
      const averageProcessingTime = embeddings.length > 0 
        ? embeddings.reduce((sum, e) => sum + e.processingTime, 0) / embeddings.length
        : 0;

      logger.info("Batch embedding generation completed", {
        totalTexts: request.texts.length,
        successCount,
        errorCount,
        totalProcessingTime,
        averageProcessingTime,
      });

      return {
        embeddings,
        totalTexts: request.texts.length,
        successCount,
        errorCount,
        totalProcessingTime,
        averageProcessingTime,
      };

    } catch (error) {
      const totalProcessingTime = Date.now() - startTime;
      
      logger.error("Batch embedding generation failed", {
        error: error instanceof Error ? error.message : String(error),
        totalTexts: request.texts.length,
        successCount,
        errorCount,
        totalProcessingTime,
      });

      throw new RAGError(
        "batch_embedding",
        `Batch embedding generation failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Calculate cosine similarity between two embeddings
   */
  calculateSimilarity(embedding1: number[], embedding2: number[]): number {
    if (embedding1.length !== embedding2.length) {
      throw new RAGError("similarity", "Embeddings must have the same dimensions");
    }

    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;

    for (let i = 0; i < embedding1.length; i++) {
      dotProduct += embedding1[i] * embedding2[i];
      norm1 += embedding1[i] * embedding1[i];
      norm2 += embedding2[i] * embedding2[i];
    }

    const magnitude = Math.sqrt(norm1) * Math.sqrt(norm2);
    
    if (magnitude === 0) {
      return 0;
    }

    return dotProduct / magnitude;
  }

  /**
   * Validate embedding dimensions
   */
  validateEmbedding(embedding: number[]): boolean {
    if (!Array.isArray(embedding)) {
      return false;
    }

    if (embedding.length !== this.dimensions) {
      return false;
    }

    return embedding.every(value => typeof value === "number" && !isNaN(value));
  }

  /**
   * Get service statistics
   */
  getServiceInfo() {
    return {
      model: this.model,
      dimensions: this.dimensions,
      maxTextLength: this.maxTextLength,
      batchSize: this.batchSize,
    };
  }
}
