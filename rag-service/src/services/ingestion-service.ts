/**
 * Ingestion Service for Scientific Data Sources
 */

import * as admin from "firebase-admin";
import { GBIFClient, GBIFSpecies, GBIFOccurrence } from "../data-sources/gbif-client";
import { IUCNClient, IUCNSpecies, IUCNAssessment } from "../data-sources/iucn-client";
import { OBISClient, OBISOccurrence } from "../data-sources/obis-client";
import { EBirdClient, EBirdObservation } from "../data-sources/ebird-client";
import { EmbeddingService } from "./embedding-service";
import { FirestoreService, DocumentMetadata } from "./firestore-service";
import { config } from "../config/environment";
import { logger, logIngestion } from "../utils/logger";
import { IngestionError } from "../utils/error-handler";

export interface IngestionJobConfig {
  source: "gbif" | "iucn" | "obis" | "ebird";
  parameters: {
    species?: string;
    location?: {
      country?: string;
      coordinates?: {
        latitude: number;
        longitude: number;
        radius?: number;
      };
    };
    dateRange?: {
      start: string;
      end: string;
    };
    limit?: number;
    categories?: string[];
    types?: string[];
  };
  options?: {
    chunkSize?: number;
    chunkOverlap?: number;
    batchSize?: number;
    generateEmbeddings?: boolean;
  };
}

export interface IngestionJobStatus {
  jobId: string;
  source: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: {
    phase: "fetching" | "processing" | "embedding" | "storing" | "completed";
    processed: number;
    total: number;
    percentage: number;
  };
  results?: {
    documentsIngested: number;
    embeddingsCreated: number;
    errors: number;
    errorMessages?: string[];
  };
  config: IngestionJobConfig;
  createdAt: admin.firestore.Timestamp;
  startedAt?: admin.firestore.Timestamp;
  completedAt?: admin.firestore.Timestamp;
  error?: string;
}

export interface ProcessedDocument {
  content: string;
  metadata: DocumentMetadata;
  chunks?: string[];
}

export class IngestionService {
  private gbifClient: GBIFClient;
  private iucnClient: IUCNClient;
  private obisClient: OBISClient;
  private ebirdClient: EBirdClient;
  private embeddingService: EmbeddingService;
  private firestoreService: FirestoreService;
  private db: admin.firestore.Firestore;
  private ingestionJobsCollection: string;

  constructor() {
    this.gbifClient = new GBIFClient();
    this.iucnClient = new IUCNClient();
    this.obisClient = new OBISClient();
    this.ebirdClient = new EBirdClient();
    this.embeddingService = new EmbeddingService();
    this.firestoreService = new FirestoreService();
    this.db = admin.firestore();
    this.ingestionJobsCollection = config.firestore.collections.ingestionJobs;
  }

  /**
   * Start an ingestion job
   */
  async startIngestionJob(config: IngestionJobConfig): Promise<string> {
    const jobId = `${config.source}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    try {
      // Create job record
      const jobStatus: Omit<IngestionJobStatus, "jobId"> = {
        source: config.source,
        status: "queued",
        progress: {
          phase: "fetching",
          processed: 0,
          total: 0,
          percentage: 0,
        },
        config,
        createdAt: admin.firestore.Timestamp.now(),
      };

      await this.db.collection(this.ingestionJobsCollection).doc(jobId).set(jobStatus);

      logger.info("Ingestion job created", { jobId, source: config.source, config });

      // Start processing asynchronously
      this.processIngestionJob(jobId, config).catch(error => {
        logger.error("Ingestion job failed", {
          jobId,
          error: error instanceof Error ? error.message : String(error),
        });
      });

      return jobId;

    } catch (error) {
      logger.error("Failed to create ingestion job", {
        jobId,
        error: error instanceof Error ? error.message : String(error),
      });

      throw new IngestionError(
        config.source,
        `Failed to create ingestion job: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Get ingestion job status
   */
  async getJobStatus(jobId: string): Promise<IngestionJobStatus | null> {
    try {
      const doc = await this.db.collection(this.ingestionJobsCollection).doc(jobId).get();
      
      if (!doc.exists) {
        return null;
      }

      return {
        jobId,
        ...doc.data(),
      } as IngestionJobStatus;

    } catch (error) {
      logger.error("Failed to get job status", {
        jobId,
        error: error instanceof Error ? error.message : String(error),
      });

      throw new IngestionError(
        "unknown",
        `Failed to get job status: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Cancel an ingestion job
   */
  async cancelJob(jobId: string): Promise<void> {
    try {
      await this.db.collection(this.ingestionJobsCollection).doc(jobId).update({
        status: "cancelled",
        completedAt: admin.firestore.Timestamp.now(),
      });

      logger.info("Ingestion job cancelled", { jobId });

    } catch (error) {
      logger.error("Failed to cancel job", {
        jobId,
        error: error instanceof Error ? error.message : String(error),
      });

      throw new IngestionError(
        "unknown",
        `Failed to cancel job: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * List ingestion jobs
   */
  async listJobs(filters?: {
    source?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<{
    jobs: IngestionJobStatus[];
    total: number;
  }> {
    try {
      let query: admin.firestore.Query = this.db.collection(this.ingestionJobsCollection);

      // Apply filters
      if (filters?.source) {
        query = query.where("source", "==", filters.source);
      }
      
      if (filters?.status) {
        query = query.where("status", "==", filters.status);
      }

      // Order by creation date (newest first)
      query = query.orderBy("createdAt", "desc");

      // Apply pagination
      if (filters?.offset) {
        query = query.offset(filters.offset);
      }
      
      if (filters?.limit) {
        query = query.limit(filters.limit);
      }

      const snapshot = await query.get();
      
      const jobs: IngestionJobStatus[] = snapshot.docs.map(doc => ({
        jobId: doc.id,
        ...doc.data(),
      } as IngestionJobStatus));

      // Get total count (simplified - in production, use a separate count query)
      const totalSnapshot = await this.db.collection(this.ingestionJobsCollection).count().get();
      const total = totalSnapshot.data().count;

      return { jobs, total };

    } catch (error) {
      logger.error("Failed to list jobs", {
        error: error instanceof Error ? error.message : String(error),
        filters,
      });

      throw new IngestionError(
        "unknown",
        `Failed to list jobs: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Process an ingestion job
   */
  private async processIngestionJob(jobId: string, jobConfig: IngestionJobConfig): Promise<void> {
    const startTime = Date.now();

    try {
      // Update job status to running
      await this.updateJobStatus(jobId, {
        status: "running",
        startedAt: admin.firestore.Timestamp.now(),
      });

      logger.info("Starting ingestion job processing", { jobId, source: jobConfig.source });

      // Fetch data from source
      const rawData = await this.fetchDataFromSource(jobId, jobConfig);

      // Process and chunk documents
      const documents = await this.processDocuments(jobId, rawData, jobConfig);

      // Generate embeddings and store
      const results = await this.storeDocumentsWithEmbeddings(jobId, documents, jobConfig);

      // Update job as completed
      await this.updateJobStatus(jobId, {
        status: "completed",
        completedAt: admin.firestore.Timestamp.now(),
        progress: {
          phase: "completed",
          processed: results.documentsIngested,
          total: results.documentsIngested,
          percentage: 100,
        },
        results,
      });

      const duration = Date.now() - startTime;

      logIngestion(jobConfig.source, results.documentsIngested, duration);

      logger.info("Ingestion job completed successfully", {
        jobId,
        source: jobConfig.source,
        duration,
        results,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      await this.updateJobStatus(jobId, {
        status: "failed",
        completedAt: admin.firestore.Timestamp.now(),
        error: errorMessage,
      });

      logIngestion(jobConfig.source, 0, duration);

      logger.error("Ingestion job failed", {
        jobId,
        source: jobConfig.source,
        duration,
        error: errorMessage,
      });

      throw error;
    }
  }

  /**
   * Update job status
   */
  private async updateJobStatus(jobId: string, updates: Partial<IngestionJobStatus>): Promise<void> {
    try {
      await this.db.collection(this.ingestionJobsCollection).doc(jobId).update(updates);
    } catch (error) {
      logger.error("Failed to update job status", {
        jobId,
        updates,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  /**
   * Fetch data from the specified source
   */
  private async fetchDataFromSource(jobId: string, jobConfig: IngestionJobConfig): Promise<any[]> {
    const { source, parameters } = jobConfig;
    const limit = parameters.limit || 100;

    await this.updateJobStatus(jobId, {
      progress: {
        phase: "fetching",
        processed: 0,
        total: limit,
        percentage: 0,
      },
    });

    try {
      switch (source) {
        case "gbif":
          return await this.fetchGBIFData(parameters, limit);

        case "iucn":
          return await this.fetchIUCNData(parameters, limit);

        case "obis":
          return await this.fetchOBISData(parameters, limit);

        case "ebird":
          return await this.fetchEBirdData(parameters, limit);

        default:
          throw new IngestionError(source, `Unsupported data source: ${source}`);
      }
    } catch (error) {
      throw new IngestionError(
        source,
        `Failed to fetch data from ${source}: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  /**
   * Fetch GBIF data
   */
  private async fetchGBIFData(parameters: any, limit: number): Promise<(GBIFSpecies | GBIFOccurrence)[]> {
    const results: (GBIFSpecies | GBIFOccurrence)[] = [];

    if (parameters.species) {
      // Search for specific species
      const speciesResponse = await this.gbifClient.searchSpecies({
        q: parameters.species,
        limit,
      });
      results.push(...speciesResponse.results);
    } else if (parameters.location?.coordinates) {
      // Search by location
      const occurrenceResponse = await this.gbifClient.searchSpeciesByLocation(
        parameters.location.coordinates.latitude,
        parameters.location.coordinates.longitude,
        parameters.location.coordinates.radius,
        limit
      );
      results.push(...occurrenceResponse.results);
    } else {
      // Get Brazilian species by default
      const brazilianResponse = await this.gbifClient.getBrazilianSpecies(limit);
      results.push(...brazilianResponse.results);
    }

    return results;
  }

  /**
   * Fetch IUCN data
   */
  private async fetchIUCNData(parameters: any, limit: number): Promise<(IUCNSpecies | IUCNAssessment)[]> {
    const results: (IUCNSpecies | IUCNAssessment)[] = [];

    if (parameters.species) {
      // Search for specific species
      const speciesResponse = await this.iucnClient.getSpeciesByName(parameters.species);
      results.push(...speciesResponse.result);
    } else if (parameters.categories && parameters.categories.length > 0) {
      // Get species by conservation category
      for (const category of parameters.categories) {
        const categoryResponse = await this.iucnClient.getSpeciesByCategory(category);
        results.push(...categoryResponse.result.slice(0, Math.floor(limit / parameters.categories.length)));
      }
    } else {
      // Get Brazilian threatened species by default
      const brazilianResponse = await this.iucnClient.getBrazilianThreatenedSpecies();
      results.push(...brazilianResponse.result.slice(0, limit));
    }

    return results;
  }

  /**
   * Fetch OBIS data
   */
  private async fetchOBISData(parameters: any, limit: number): Promise<OBISOccurrence[]> {
    if (parameters.location?.coordinates) {
      // Search by location
      const response = await this.obisClient.searchBrazilianMarineSpecies(
        parameters.location.coordinates.latitude,
        parameters.location.coordinates.longitude,
        parameters.location.coordinates.radius,
        limit
      );
      return response.results;
    } else {
      // Get Brazilian marine species by default
      const response = await this.obisClient.searchBrazilianMarineSpecies(undefined, undefined, undefined, limit);
      return response.results;
    }
  }

  /**
   * Fetch eBird data
   */
  private async fetchEBirdData(parameters: any, limit: number): Promise<EBirdObservation[]> {
    if (parameters.location?.coordinates) {
      // Search by location
      return await this.ebirdClient.getNearbyObservations(
        parameters.location.coordinates.latitude,
        parameters.location.coordinates.longitude,
        { maxResults: limit }
      );
    } else {
      // Get Brazilian bird observations by default
      return await this.ebirdClient.getBrazilianBirdObservations({ maxResults: limit });
    }
  }

  /**
   * Process raw data into documents
   */
  private async processDocuments(
    jobId: string,
    rawData: any[],
    jobConfig: IngestionJobConfig
  ): Promise<ProcessedDocument[]> {
    const documents: ProcessedDocument[] = [];
    const chunkSize = jobConfig.options?.chunkSize || config.rag.chunkSize;
    const chunkOverlap = jobConfig.options?.chunkOverlap || config.rag.chunkOverlap;

    await this.updateJobStatus(jobId, {
      progress: {
        phase: "processing",
        processed: 0,
        total: rawData.length,
        percentage: 0,
      },
    });

    for (let i = 0; i < rawData.length; i++) {
      try {
        const item = rawData[i];
        const processedDoc = await this.processDataItem(item, jobConfig.source);

        if (processedDoc) {
          // Chunk the document if it's too long
          if (processedDoc.content.length > chunkSize) {
            processedDoc.chunks = this.chunkText(processedDoc.content, chunkSize, chunkOverlap);
          }

          documents.push(processedDoc);
        }

        // Update progress
        const percentage = Math.round(((i + 1) / rawData.length) * 100);
        await this.updateJobStatus(jobId, {
          progress: {
            phase: "processing",
            processed: i + 1,
            total: rawData.length,
            percentage,
          },
        });

      } catch (error) {
        logger.error("Failed to process data item", {
          jobId,
          itemIndex: i,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    logger.info("Document processing completed", {
      jobId,
      totalItems: rawData.length,
      processedDocuments: documents.length,
    });

    return documents;
  }

  /**
   * Process a single data item into a document
   */
  private async processDataItem(item: any, source: string): Promise<ProcessedDocument | null> {
    try {
      switch (source) {
        case "gbif":
          return this.processGBIFItem(item);

        case "iucn":
          return this.processIUCNItem(item);

        case "obis":
          return this.processOBISItem(item);

        case "ebird":
          return this.processEBirdItem(item);

        default:
          return null;
      }
    } catch (error) {
      logger.error("Failed to process data item", {
        source,
        error: error instanceof Error ? error.message : String(error),
        item: JSON.stringify(item).substring(0, 200),
      });
      return null;
    }
  }

  /**
   * Process GBIF item
   */
  private processGBIFItem(item: GBIFSpecies | GBIFOccurrence): ProcessedDocument {
    const isSpecies = 'scientificName' in item && 'rank' in item;

    let content: string;
    let type: "species" | "occurrence";

    if (isSpecies) {
      const species = item as GBIFSpecies;
      type = "species";
      content = `Scientific Name: ${species.scientificName}
Common Name: ${species.vernacularName || 'N/A'}
Kingdom: ${species.kingdom || 'N/A'}
Phylum: ${species.phylum || 'N/A'}
Class: ${species.class || 'N/A'}
Order: ${species.order || 'N/A'}
Family: ${species.family || 'N/A'}
Genus: ${species.genus || 'N/A'}
Rank: ${species.rank || 'N/A'}
Taxonomic Status: ${species.taxonomicStatus || 'N/A'}
${species.remarks ? `Remarks: ${species.remarks}` : ''}`;
    } else {
      const occurrence = item as GBIFOccurrence;
      type = "occurrence";
      content = `Scientific Name: ${occurrence.scientificName || 'N/A'}
Kingdom: ${occurrence.kingdom || 'N/A'}
Phylum: ${occurrence.phylum || 'N/A'}
Class: ${occurrence.class || 'N/A'}
Order: ${occurrence.order || 'N/A'}
Family: ${occurrence.family || 'N/A'}
Genus: ${occurrence.genus || 'N/A'}
Species: ${occurrence.species || 'N/A'}
Location: ${occurrence.locality || 'N/A'}
Country: ${occurrence.country || 'N/A'}
Coordinates: ${occurrence.decimalLatitude && occurrence.decimalLongitude
  ? `${occurrence.decimalLatitude}, ${occurrence.decimalLongitude}`
  : 'N/A'}
Date: ${occurrence.eventDate || 'N/A'}
Basis of Record: ${occurrence.basisOfRecord || 'N/A'}
Institution: ${occurrence.institutionCode || 'N/A'}`;
    }

    const metadata: DocumentMetadata = {
      source: "gbif",
      type,
      scientificName: item.scientificName,
      location: {
        country: (item as GBIFOccurrence).country || "BR",
        coordinates: (item as GBIFOccurrence).decimalLatitude && (item as GBIFOccurrence).decimalLongitude
          ? {
              latitude: (item as GBIFOccurrence).decimalLatitude!,
              longitude: (item as GBIFOccurrence).decimalLongitude!,
            }
          : undefined,
      },
      timestamp: admin.firestore.Timestamp.now(),
      originalId: String(item.key),
    };

    return { content, metadata };
  }

  /**
   * Process IUCN item
   */
  private processIUCNItem(item: IUCNSpecies | IUCNAssessment): ProcessedDocument {
    const isSpecies = 'kingdom' in item;
    const content = `Scientific Name: ${item.scientific_name}
Kingdom: ${isSpecies ? item.kingdom : 'N/A'}
Phylum: ${isSpecies ? item.phylum : 'N/A'}
Class: ${isSpecies ? item.class : 'N/A'}
Order: ${isSpecies ? item.order : 'N/A'}
Family: ${isSpecies ? item.family : 'N/A'}
Genus: ${isSpecies ? item.genus : 'N/A'}
Conservation Status: ${item.category}
Population Trend: ${item.population_trend || 'N/A'}
Marine System: ${item.marine_system ? 'Yes' : 'No'}
Freshwater System: ${item.freshwater_system ? 'Yes' : 'No'}
Terrestrial System: ${item.terrestrial_system ? 'Yes' : 'No'}
Assessment Date: ${item.assessment_date || 'N/A'}
Criteria: ${item.criteria || 'N/A'}
${item.aoo_km2 ? `Area of Occupancy: ${item.aoo_km2} km²` : ''}
${item.eoo_km2 ? `Extent of Occurrence: ${item.eoo_km2} km²` : ''}`;

    const metadata: DocumentMetadata = {
      source: "iucn",
      type: "assessment",
      category: item.category,
      scientificName: item.scientific_name,
      timestamp: admin.firestore.Timestamp.now(),
      originalId: String(item.taxonid),
    };

    return { content, metadata };
  }

  /**
   * Process OBIS item
   */
  private processOBISItem(item: OBISOccurrence): ProcessedDocument {
    const content = `Scientific Name: ${item.scientificName || 'N/A'}
Kingdom: ${item.kingdom || 'N/A'}
Phylum: ${item.phylum || 'N/A'}
Class: ${item.class || 'N/A'}
Order: ${item.order || 'N/A'}
Family: ${item.family || 'N/A'}
Genus: ${item.genus || 'N/A'}
Species: ${item.species || 'N/A'}
Location: ${item.locality || 'N/A'}
Country: ${item.country || 'N/A'}
Coordinates: ${item.decimalLatitude && item.decimalLongitude
  ? `${item.decimalLatitude}, ${item.decimalLongitude}`
  : 'N/A'}
Date: ${item.date_start || 'N/A'}
Depth: ${item.minimumDepthInMeters && item.maximumDepthInMeters
  ? `${item.minimumDepthInMeters}-${item.maximumDepthInMeters}m`
  : 'N/A'}
Habitat: ${item.habitat || 'N/A'}
Marine: ${item.marine ? 'Yes' : 'No'}
Brackish: ${item.brackish ? 'Yes' : 'No'}
Freshwater: ${item.freshwater ? 'Yes' : 'No'}
Conservation Status: ${item.redlist_category || 'N/A'}
Dataset: ${item.datasetName || 'N/A'}`;

    const metadata: DocumentMetadata = {
      source: "obis",
      type: "occurrence",
      scientificName: item.scientificName,
      location: {
        country: item.country || undefined,
        coordinates: item.decimalLatitude && item.decimalLongitude
          ? {
              latitude: item.decimalLatitude,
              longitude: item.decimalLongitude,
            }
          : undefined,
      },
      timestamp: admin.firestore.Timestamp.now(),
      originalId: item.id,
    };

    return { content, metadata };
  }

  /**
   * Process eBird item
   */
  private processEBirdItem(item: EBirdObservation): ProcessedDocument {
    const content = `Scientific Name: ${item.sciName}
Common Name: ${item.comName}
Species Code: ${item.speciesCode}
Location: ${item.locName}
Country: ${item.countryName}
State/Province: ${item.subnational1Name || 'N/A'}
Coordinates: ${item.lat}, ${item.lng}
Date: ${item.obsDt}
Count: ${item.howMany || 'Present'}
Observer: ${item.userDisplayName || 'N/A'}
Checklist ID: ${item.checklistId || 'N/A'}
Valid: ${item.obsValid ? 'Yes' : 'No'}
Reviewed: ${item.obsReviewed ? 'Yes' : 'No'}`;

    const metadata: DocumentMetadata = {
      source: "ebird",
      type: "observation",
      scientificName: item.sciName,
      commonName: item.comName,
      location: {
        country: item.countryCode,
        coordinates: {
          latitude: item.lat,
          longitude: item.lng,
        },
      },
      timestamp: admin.firestore.Timestamp.now(),
      originalId: item.obsId || item.checklistId,
    };

    return { content, metadata };
  }

  /**
   * Chunk text into smaller pieces
   */
  private chunkText(text: string, chunkSize: number, overlap: number): string[] {
    const chunks: string[] = [];
    let start = 0;

    while (start < text.length) {
      const end = Math.min(start + chunkSize, text.length);
      const chunk = text.substring(start, end);
      chunks.push(chunk);

      if (end === text.length) break;
      start = end - overlap;
    }

    return chunks;
  }

  /**
   * Store documents with embeddings
   */
  private async storeDocumentsWithEmbeddings(
    jobId: string,
    documents: ProcessedDocument[],
    jobConfig: IngestionJobConfig
  ): Promise<{
    documentsIngested: number;
    embeddingsCreated: number;
    errors: number;
  }> {
    let documentsIngested = 0;
    let embeddingsCreated = 0;
    let errors = 0;

    const generateEmbeddings = jobConfig.options?.generateEmbeddings !== false;
    const batchSize = jobConfig.options?.batchSize || 10;

    await this.updateJobStatus(jobId, {
      progress: {
        phase: "storing",
        processed: 0,
        total: documents.length,
        percentage: 0,
      },
    });

    // Process documents in batches
    for (let i = 0; i < documents.length; i += batchSize) {
      const batch = documents.slice(i, i + batchSize);

      for (const doc of batch) {
        try {
          // Store main document
          const documentId = await this.firestoreService.storeDocument(doc.content, doc.metadata);
          documentsIngested++;

          if (generateEmbeddings) {
            // Generate and store embeddings for main content
            const embeddingResponse = await this.embeddingService.generateEmbedding({
              text: doc.content,
              metadata: { documentId, ...doc.metadata },
            });

            await this.firestoreService.storeEmbedding(
              documentId,
              embeddingResponse.embedding,
              doc.content,
              doc.metadata,
              embeddingResponse.model
            );
            embeddingsCreated++;

            // Generate embeddings for chunks if they exist
            if (doc.chunks && doc.chunks.length > 0) {
              for (let chunkIndex = 0; chunkIndex < doc.chunks.length; chunkIndex++) {
                const chunk = doc.chunks[chunkIndex];

                const chunkEmbeddingResponse = await this.embeddingService.generateEmbedding({
                  text: chunk,
                  metadata: {
                    documentId,
                    chunkIndex,
                    totalChunks: doc.chunks.length,
                    ...doc.metadata
                  },
                });

                await this.firestoreService.storeEmbedding(
                  documentId,
                  chunkEmbeddingResponse.embedding,
                  chunk,
                  { ...doc.metadata, chunkIndex, totalChunks: doc.chunks.length },
                  chunkEmbeddingResponse.model
                );
                embeddingsCreated++;
              }
            }
          }

        } catch (error) {
          errors++;
          logger.error("Failed to store document", {
            jobId,
            error: error instanceof Error ? error.message : String(error),
            documentPreview: doc.content.substring(0, 100),
          });
        }
      }

      // Update progress
      const processed = Math.min(i + batchSize, documents.length);
      const percentage = Math.round((processed / documents.length) * 100);

      await this.updateJobStatus(jobId, {
        progress: {
          phase: "storing",
          processed,
          total: documents.length,
          percentage,
        },
      });

      // Small delay between batches
      if (i + batchSize < documents.length) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }

    return { documentsIngested, embeddingsCreated, errors };
  }
}
