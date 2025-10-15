/**
 * GBIF (Global Biodiversity Information Facility) API Client
 * https://www.gbif.org/developer/summary
 */

import { config } from "../config/environment";
import { logger, logDataSourceOperation } from "../utils/logger";
import { ExternalServiceError } from "../utils/error-handler";

// GBIF API interfaces
export interface GBIFSpeciesSearchParams {
  q?: string;
  kingdom?: string;
  phylum?: string;
  class?: string;
  order?: string;
  family?: string;
  genus?: string;
  species?: string;
  rank?: string;
  status?: string;
  isExtinct?: boolean;
  habitat?: string;
  threat?: string;
  nameType?: string;
  datasetKey?: string;
  limit?: number;
  offset?: number;
}

export interface GBIFOccurrenceSearchParams {
  taxonKey?: number;
  scientificName?: string;
  country?: string;
  publishingCountry?: string;
  hasCoordinate?: boolean;
  hasGeospatialIssue?: boolean;
  decimalLatitude?: number;
  decimalLongitude?: number;
  year?: number;
  month?: number;
  basisOfRecord?: string;
  datasetKey?: string;
  publishingOrg?: string;
  elevation?: number;
  depth?: number;
  institutionCode?: string;
  collectionCode?: string;
  catalogNumber?: string;
  recordedBy?: string;
  identifiedBy?: string;
  limit?: number;
  offset?: number;
}

export interface GBIFSpecies {
  key: number;
  nubKey?: number;
  nameKey?: number;
  taxonID?: string;
  sourceTaxonKey?: number;
  kingdom?: string;
  phylum?: string;
  class?: string;
  order?: string;
  family?: string;
  genus?: string;
  species?: string;
  kingdomKey?: number;
  phylumKey?: number;
  classKey?: number;
  orderKey?: number;
  familyKey?: number;
  genusKey?: number;
  speciesKey?: number;
  datasetKey: string;
  constituentKey?: string;
  parentKey?: number;
  parent?: string;
  acceptedKey?: number;
  accepted?: string;
  basionymKey?: number;
  basionym?: string;
  scientificName: string;
  canonicalName?: string;
  vernacularName?: string;
  authorship?: string;
  nameType?: string;
  rank?: string;
  origin?: string;
  taxonomicStatus?: string;
  nomenclaturalStatus?: string[];
  remarks?: string;
  numDescendants?: number;
  lastCrawled?: string;
  lastInterpreted?: string;
  issues?: string[];
  synonym?: boolean;
}

export interface GBIFOccurrence {
  key: number;
  datasetKey: string;
  publishingOrgKey: string;
  installationKey?: string;
  publishingCountry?: string;
  protocol?: string;
  lastCrawled?: string;
  lastParsed?: string;
  crawlId?: number;
  extensions?: Record<string, any>;
  basisOfRecord?: string;
  taxonKey?: number;
  kingdomKey?: number;
  phylumKey?: number;
  classKey?: number;
  orderKey?: number;
  familyKey?: number;
  genusKey?: number;
  speciesKey?: number;
  scientificName?: string;
  kingdom?: string;
  phylum?: string;
  class?: string;
  order?: string;
  family?: string;
  genus?: string;
  species?: string;
  genericName?: string;
  specificEpithet?: string;
  taxonRank?: string;
  dateIdentified?: string;
  decimalLatitude?: number;
  decimalLongitude?: number;
  coordinateUncertaintyInMeters?: number;
  coordinatePrecision?: number;
  elevation?: number;
  elevationAccuracy?: number;
  depth?: number;
  depthAccuracy?: number;
  eventDate?: string;
  day?: number;
  month?: number;
  year?: number;
  verbatimEventDate?: string;
  verbatimLocality?: string;
  country?: string;
  countryCode?: string;
  stateProvince?: string;
  waterBody?: string;
  locality?: string;
  institutionCode?: string;
  collectionCode?: string;
  catalogNumber?: string;
  recordNumber?: string;
  identifiedBy?: string;
  recordedBy?: string;
  typeStatus?: string;
  establishmentMeans?: string;
  lastInterpreted?: string;
  mediaType?: string[];
  issues?: string[];
}

export interface GBIFSearchResponse<T> {
  offset: number;
  limit: number;
  endOfRecords: boolean;
  count: number;
  results: T[];
}

export class GBIFClient {
  private baseUrl: string;
  private timeout: number;

  constructor() {
    this.baseUrl = config.dataSources.gbif.apiUrl;
    this.timeout = config.dataSources.gbif.timeout;
  }

  private async makeRequest<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const startTime = Date.now();
    const url = new URL(endpoint, this.baseUrl);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url.toString(), {
        method: "GET",
        headers: {
          "Accept": "application/json",
          "User-Agent": "SIRA-RAG-Service/1.0.0",
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new ExternalServiceError(
          "GBIF",
          `HTTP ${response.status}: ${response.statusText}`,
          response.status
        );
      }

      const data = await response.json() as T;
      const duration = Date.now() - startTime;

      logDataSourceOperation("GBIF", endpoint, "success", duration, {
        url: url.toString(),
        statusCode: response.status,
      });

      return data;

    } catch (error) {
      const duration = Date.now() - startTime;
      
      logDataSourceOperation("GBIF", endpoint, "error", duration, {
        url: url.toString(),
        error: error instanceof Error ? error.message : String(error),
      });

      if (error instanceof ExternalServiceError) {
        throw error;
      }

      throw new ExternalServiceError(
        "GBIF",
        `Request failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  // Search species
  async searchSpecies(params: GBIFSpeciesSearchParams = {}): Promise<GBIFSearchResponse<GBIFSpecies>> {
    logger.info("GBIF species search", { params });
    return this.makeRequest<GBIFSearchResponse<GBIFSpecies>>("/species/search", params);
  }

  // Get species by key
  async getSpecies(key: number): Promise<GBIFSpecies> {
    logger.info("GBIF get species", { key });
    return this.makeRequest<GBIFSpecies>(`/species/${key}`);
  }

  // Search occurrences
  async searchOccurrences(params: GBIFOccurrenceSearchParams = {}): Promise<GBIFSearchResponse<GBIFOccurrence>> {
    logger.info("GBIF occurrence search", { params });
    return this.makeRequest<GBIFSearchResponse<GBIFOccurrence>>("/occurrence/search", params);
  }

  // Get occurrence by key
  async getOccurrence(key: number): Promise<GBIFOccurrence> {
    logger.info("GBIF get occurrence", { key });
    return this.makeRequest<GBIFOccurrence>(`/occurrence/${key}`);
  }

  // Search species by location (Brazil focus)
  async searchSpeciesByLocation(
    latitude: number,
    longitude: number,
    radius: number = 50000, // 50km radius
    limit: number = 100
  ): Promise<GBIFSearchResponse<GBIFOccurrence>> {
    const params: GBIFOccurrenceSearchParams = {
      decimalLatitude: latitude,
      decimalLongitude: longitude,
      hasCoordinate: true,
      country: "BR", // Brazil
      limit,
    };

    return this.searchOccurrences(params);
  }

  // Get Brazilian endemic species
  async getBrazilianSpecies(limit: number = 1000): Promise<GBIFSearchResponse<GBIFOccurrence>> {
    const params: GBIFOccurrenceSearchParams = {
      country: "BR",
      hasCoordinate: true,
      basisOfRecord: "HUMAN_OBSERVATION,MACHINE_OBSERVATION,OBSERVATION",
      limit,
    };

    return this.searchOccurrences(params);
  }

  // Health check
  async healthCheck(): Promise<{ status: "healthy" | "unhealthy"; responseTime: number }> {
    const startTime = Date.now();
    
    try {
      await this.makeRequest("/species/search", { limit: 1 });
      
      return {
        status: "healthy",
        responseTime: Date.now() - startTime,
      };
    } catch (error) {
      return {
        status: "unhealthy",
        responseTime: Date.now() - startTime,
      };
    }
  }
}
