/**
 * Firestore Service for Vector Storage and Retrieval
 */

import * as admin from "firebase-admin";
import { config } from "../config/environment";
import { logger, logPerformance } from "../utils/logger";
import { RAGError } from "../utils/error-handler";

export interface DocumentMetadata {
  source: "gbif" | "iucn" | "obis" | "ebird";
  type: "species" | "occurrence" | "assessment" | "observation" | "habitat" | "threat";
  category?: string;
  scientificName?: string;
  commonName?: string;
  location?: {
    country?: string;
    coordinates?: {
      latitude: number;
      longitude: number;
    };
  };
  timestamp: admin.firestore.Timestamp;
  ingestionJobId?: string;
  originalId?: string;
  url?: string;
  [key: string]: any;
}

export interface StoredDocument {
  id: string;
  content: string;
  metadata: DocumentMetadata;
  chunkIndex?: number;
  totalChunks?: number;
  createdAt: admin.firestore.Timestamp;
  updatedAt: admin.firestore.Timestamp;
}

export interface StoredEmbedding {
  id: string;
  documentId: string;
  embedding: number[];
  content: string;
  metadata: DocumentMetadata;
  model: string;
  dimensions: number;
  createdAt: admin.firestore.Timestamp;
}

export interface VectorSearchQuery {
  embedding: number[];
  limit?: number;
  threshold?: number;
  filters?: {
    source?: string[];
    type?: string[];
    category?: string[];
    scientificName?: string;
    location?: {
      country?: string;
      coordinates?: {
        latitude: number;
        longitude: number;
        radius?: number; // in kilometers
      };
    };
  };
}

export interface VectorSearchResult {
  id: string;
  content: string;
  metadata: DocumentMetadata;
  score: number;
  documentId: string;
}

export interface VectorSearchResponse {
  results: VectorSearchResult[];
  totalResults: number;
  processingTime: number;
  query: {
    limit: number;
    threshold: number;
    filters?: any;
  };
}

export class FirestoreService {
  private db: admin.firestore.Firestore;
  private knowledgeBaseCollection: string;
  private embeddingsCollection: string;

  constructor() {
    this.db = admin.firestore();
    this.knowledgeBaseCollection = config.firestore.collections.knowledgeBase;
    this.embeddingsCollection = config.firestore.collections.embeddings;
  }

  /**
   * Store a document in the knowledge base
   */
  async storeDocument(content: string, metadata: DocumentMetadata): Promise<string> {
    const startTime = Date.now();
    
    try {
      const document: Omit<StoredDocument, "id"> = {
        content,
        metadata,
        createdAt: admin.firestore.Timestamp.now(),
        updatedAt: admin.firestore.Timestamp.now(),
      };

      const docRef = await this.db.collection(this.knowledgeBaseCollection).add(document);
      
      const processingTime = Date.now() - startTime;
      
      logPerformance("document_storage", processingTime, {
        documentId: docRef.id,
        contentLength: content.length,
        source: metadata.source,
        type: metadata.type,
      });

      logger.info("Document stored successfully", {
        documentId: docRef.id,
        source: metadata.source,
        type: metadata.type,
        contentLength: content.length,
      });

      return docRef.id;

    } catch (error) {
      const processingTime = Date.now() - startTime;
      
      logger.error("Failed to store document", {
        error: error instanceof Error ? error.message : String(error),
        source: metadata.source,
        type: metadata.type,
        contentLength: content.length,
        processingTime,
      });

      throw new RAGError(
        "document_storage",
        `Failed to store document: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Store an embedding
   */
  async storeEmbedding(
    documentId: string,
    embedding: number[],
    content: string,
    metadata: DocumentMetadata,
    model: string
  ): Promise<string> {
    const startTime = Date.now();
    
    try {
      const embeddingDoc: Omit<StoredEmbedding, "id"> = {
        documentId,
        embedding,
        content,
        metadata,
        model,
        dimensions: embedding.length,
        createdAt: admin.firestore.Timestamp.now(),
      };

      const embeddingRef = await this.db.collection(this.embeddingsCollection).add(embeddingDoc);
      
      const processingTime = Date.now() - startTime;
      
      logPerformance("embedding_storage", processingTime, {
        embeddingId: embeddingRef.id,
        documentId,
        dimensions: embedding.length,
        model,
      });

      logger.info("Embedding stored successfully", {
        embeddingId: embeddingRef.id,
        documentId,
        dimensions: embedding.length,
        model,
      });

      return embeddingRef.id;

    } catch (error) {
      const processingTime = Date.now() - startTime;
      
      logger.error("Failed to store embedding", {
        error: error instanceof Error ? error.message : String(error),
        documentId,
        dimensions: embedding.length,
        model,
        processingTime,
      });

      throw new RAGError(
        "embedding_storage",
        `Failed to store embedding: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Perform vector similarity search
   * Note: This is a simplified implementation. For production, use Firestore Vector Search
   */
  async vectorSearch(query: VectorSearchQuery): Promise<VectorSearchResponse> {
    const startTime = Date.now();
    const limit = query.limit || config.rag.maxRetrievalResults;
    const threshold = query.threshold || config.rag.similarityThreshold;

    try {
      logger.info("Starting vector search", {
        limit,
        threshold,
        filters: query.filters,
        embeddingDimensions: query.embedding.length,
      });

      // Build Firestore query with filters
      let firestoreQuery: admin.firestore.Query = this.db.collection(this.embeddingsCollection);

      // Apply filters
      if (query.filters) {
        if (query.filters.source && query.filters.source.length > 0) {
          firestoreQuery = firestoreQuery.where("metadata.source", "in", query.filters.source);
        }
        
        if (query.filters.type && query.filters.type.length > 0) {
          firestoreQuery = firestoreQuery.where("metadata.type", "in", query.filters.type);
        }
        
        if (query.filters.scientificName) {
          firestoreQuery = firestoreQuery.where("metadata.scientificName", "==", query.filters.scientificName);
        }
        
        if (query.filters.location?.country) {
          firestoreQuery = firestoreQuery.where("metadata.location.country", "==", query.filters.location.country);
        }
      }

      // Execute query (limit to reasonable number for similarity calculation)
      const snapshot = await firestoreQuery.limit(Math.min(limit * 10, 1000)).get();
      
      if (snapshot.empty) {
        return {
          results: [],
          totalResults: 0,
          processingTime: Date.now() - startTime,
          query: { limit, threshold, filters: query.filters },
        };
      }

      // Calculate similarities and sort
      const candidates: Array<VectorSearchResult & { similarity: number }> = [];
      
      snapshot.docs.forEach(doc => {
        const data = doc.data() as StoredEmbedding;
        const similarity = this.calculateCosineSimilarity(query.embedding, data.embedding);
        
        if (similarity >= threshold) {
          candidates.push({
            id: doc.id,
            content: data.content,
            metadata: data.metadata,
            score: similarity,
            documentId: data.documentId,
            similarity,
          });
        }
      });

      // Sort by similarity (descending) and limit results
      candidates.sort((a, b) => b.similarity - a.similarity);
      const results = candidates.slice(0, limit).map(({ similarity, ...result }) => result);

      const processingTime = Date.now() - startTime;

      logPerformance("vector_search", processingTime, {
        totalCandidates: snapshot.size,
        filteredCandidates: candidates.length,
        finalResults: results.length,
        threshold,
        limit,
      });

      logger.info("Vector search completed", {
        totalCandidates: snapshot.size,
        filteredCandidates: candidates.length,
        finalResults: results.length,
        processingTime,
      });

      return {
        results,
        totalResults: results.length,
        processingTime,
        query: { limit, threshold, filters: query.filters },
      };

    } catch (error) {
      const processingTime = Date.now() - startTime;
      
      logger.error("Vector search failed", {
        error: error instanceof Error ? error.message : String(error),
        limit,
        threshold,
        filters: query.filters,
        processingTime,
      });

      throw new RAGError(
        "vector_search",
        `Vector search failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Get document by ID
   */
  async getDocument(documentId: string): Promise<StoredDocument | null> {
    try {
      const doc = await this.db.collection(this.knowledgeBaseCollection).doc(documentId).get();
      
      if (!doc.exists) {
        return null;
      }

      return {
        id: doc.id,
        ...doc.data(),
      } as StoredDocument;

    } catch (error) {
      logger.error("Failed to get document", {
        error: error instanceof Error ? error.message : String(error),
        documentId,
      });

      throw new RAGError(
        "document_retrieval",
        `Failed to get document: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Get collection statistics
   */
  async getStatistics(): Promise<{
    totalDocuments: number;
    totalEmbeddings: number;
    sourceBreakdown: Record<string, number>;
    typeBreakdown: Record<string, number>;
  }> {
    try {
      const [documentsSnapshot, embeddingsSnapshot] = await Promise.all([
        this.db.collection(this.knowledgeBaseCollection).count().get(),
        this.db.collection(this.embeddingsCollection).count().get(),
      ]);

      // Get source and type breakdowns (simplified - in production, use aggregation queries)
      const embeddingsQuery = await this.db.collection(this.embeddingsCollection).limit(1000).get();
      
      const sourceBreakdown: Record<string, number> = {};
      const typeBreakdown: Record<string, number> = {};

      embeddingsQuery.docs.forEach(doc => {
        const data = doc.data() as StoredEmbedding;
        const source = data.metadata.source;
        const type = data.metadata.type;

        sourceBreakdown[source] = (sourceBreakdown[source] || 0) + 1;
        typeBreakdown[type] = (typeBreakdown[type] || 0) + 1;
      });

      return {
        totalDocuments: documentsSnapshot.data().count,
        totalEmbeddings: embeddingsSnapshot.data().count,
        sourceBreakdown,
        typeBreakdown,
      };

    } catch (error) {
      logger.error("Failed to get statistics", {
        error: error instanceof Error ? error.message : String(error),
      });

      throw new RAGError(
        "statistics",
        `Failed to get statistics: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Calculate cosine similarity between two vectors
   */
  private calculateCosineSimilarity(vector1: number[], vector2: number[]): number {
    if (vector1.length !== vector2.length) {
      throw new RAGError("similarity", "Vectors must have the same dimensions");
    }

    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;

    for (let i = 0; i < vector1.length; i++) {
      dotProduct += vector1[i] * vector2[i];
      norm1 += vector1[i] * vector1[i];
      norm2 += vector2[i] * vector2[i];
    }

    const magnitude = Math.sqrt(norm1) * Math.sqrt(norm2);
    
    if (magnitude === 0) {
      return 0;
    }

    return dotProduct / magnitude;
  }
}
