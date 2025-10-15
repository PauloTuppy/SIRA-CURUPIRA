/**
 * OBIS (Ocean Biodiversity Information System) API Client
 * https://api.obis.org/
 */

import { config } from "../config/environment";
import { logger, logDataSourceOperation } from "../utils/logger";
import { ExternalServiceError } from "../utils/error-handler";

// OBIS API interfaces
export interface OBISSearchParams {
  scientificname?: string;
  taxonid?: number;
  datasetid?: string;
  nodeid?: string;
  areaid?: number;
  startdate?: string;
  enddate?: string;
  startdepth?: number;
  enddepth?: number;
  geometry?: string;
  polygon?: string;
  wkt?: string;
  redlist?: boolean;
  hab?: boolean;
  wrims?: boolean;
  dropped?: boolean;
  absence?: boolean;
  marine?: boolean;
  brackish?: boolean;
  freshwater?: boolean;
  terrestrial?: boolean;
  size?: number;
  after?: string;
  fields?: string;
}

export interface OBISOccurrence {
  id: string;
  dataset_id: string;
  decimalLongitude?: number;
  decimalLatitude?: number;
  date_start?: string;
  date_end?: string;
  date_mid?: string;
  date_year?: number;
  scientificName?: string;
  scientificNameID?: string;
  originalScientificName?: string;
  kingdom?: string;
  phylum?: string;
  class?: string;
  order?: string;
  family?: string;
  genus?: string;
  subgenus?: string;
  species?: string;
  subspecies?: string;
  variety?: string;
  forma?: string;
  aphiaID?: number;
  taxonRank?: string;
  taxonomicStatus?: string;
  redlist_category?: string;
  habitat?: string;
  wrims?: boolean;
  brackish?: boolean;
  freshwater?: boolean;
  terrestrial?: boolean;
  marine?: boolean;
  country?: string;
  locality?: string;
  minimumDepthInMeters?: number;
  maximumDepthInMeters?: number;
  coordinateUncertaintyInMeters?: number;
  individualCount?: number;
  organismQuantity?: string;
  organismQuantityType?: string;
  sex?: string;
  lifeStage?: string;
  reproductiveCondition?: string;
  behavior?: string;
  establishmentMeans?: string;
  degreeOfEstablishment?: string;
  pathway?: string;
  occurrenceStatus?: string;
  preparations?: string;
  associatedMedia?: string;
  associatedReferences?: string;
  associatedSequences?: string;
  associatedTaxa?: string;
  otherCatalogNumbers?: string;
  occurrenceRemarks?: string;
  institutionCode?: string;
  collectionCode?: string;
  datasetName?: string;
  basisOfRecord?: string;
  informationWithheld?: string;
  dataGeneralizations?: string;
  dynamicProperties?: string;
  absence?: boolean;
  marine_ecoregions?: string[];
  longhurst?: string[];
  sss?: string[];
  lme?: string[];
}

export interface OBISSearchResponse {
  total: number;
  results: OBISOccurrence[];
  last_page?: boolean;
}

export interface OBISTaxon {
  AphiaID: number;
  scientificname: string;
  authority?: string;
  status: string;
  unacceptreason?: string;
  taxonRankID: number;
  rank: string;
  valid_AphiaID?: number;
  valid_name?: string;
  valid_authority?: string;
  parentNameUsageID?: number;
  kingdom?: string;
  phylum?: string;
  class?: string;
  order?: string;
  family?: string;
  genus?: string;
  citation?: string;
  lsid?: string;
  isMarine?: boolean;
  isBrackish?: boolean;
  isFreshwater?: boolean;
  isTerrestrial?: boolean;
  isExtinct?: boolean;
  match_type?: string;
  modified?: string;
}

export interface OBISDataset {
  id: string;
  title: string;
  abstract?: string;
  citation?: string;
  homepage?: string;
  doi?: string;
  license?: string;
  created?: string;
  modified?: string;
  published?: string;
  keywords?: string[];
  contacts?: Array<{
    firstName?: string;
    lastName?: string;
    organization?: string;
    email?: string;
    role?: string;
  }>;
  extent?: {
    spatial?: {
      north?: number;
      south?: number;
      east?: number;
      west?: number;
    };
    temporal?: {
      start?: string;
      end?: string;
    };
  };
  records?: number;
  species?: number;
}

export class OBISClient {
  private baseUrl: string;
  private timeout: number;

  constructor() {
    this.baseUrl = config.dataSources.obis.apiUrl;
    this.timeout = config.dataSources.obis.timeout;
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
          "OBIS",
          `HTTP ${response.status}: ${response.statusText}`,
          response.status
        );
      }

      const data = await response.json() as T;
      const duration = Date.now() - startTime;

      logDataSourceOperation("OBIS", endpoint, "success", duration, {
        url: url.toString(),
        statusCode: response.status,
      });

      return data;

    } catch (error) {
      const duration = Date.now() - startTime;
      
      logDataSourceOperation("OBIS", endpoint, "error", duration, {
        url: url.toString(),
        error: error instanceof Error ? error.message : String(error),
      });

      if (error instanceof ExternalServiceError) {
        throw error;
      }

      throw new ExternalServiceError(
        "OBIS",
        `Request failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  // Search occurrences
  async searchOccurrences(params: OBISSearchParams = {}): Promise<OBISSearchResponse> {
    logger.info("OBIS occurrence search", { params });
    return this.makeRequest<OBISSearchResponse>("/occurrence", params);
  }

  // Get occurrence by ID
  async getOccurrence(id: string): Promise<OBISOccurrence> {
    logger.info("OBIS get occurrence", { id });
    return this.makeRequest<OBISOccurrence>(`/occurrence/${id}`);
  }

  // Search taxa
  async searchTaxa(scientificName: string): Promise<OBISTaxon[]> {
    logger.info("OBIS taxa search", { scientificName });
    return this.makeRequest<OBISTaxon[]>("/taxon", { scientificname: scientificName });
  }

  // Get taxon by AphiaID
  async getTaxon(aphiaId: number): Promise<OBISTaxon> {
    logger.info("OBIS get taxon", { aphiaId });
    return this.makeRequest<OBISTaxon>(`/taxon/${aphiaId}`);
  }

  // Get datasets
  async getDatasets(): Promise<OBISDataset[]> {
    logger.info("OBIS get datasets");
    return this.makeRequest<OBISDataset[]>("/dataset");
  }

  // Get dataset by ID
  async getDataset(id: string): Promise<OBISDataset> {
    logger.info("OBIS get dataset", { id });
    return this.makeRequest<OBISDataset>(`/dataset/${id}`);
  }

  // Search marine species by location (Brazilian coast)
  async searchBrazilianMarineSpecies(
    latitude?: number,
    longitude?: number,
    radius?: number,
    size: number = 100
  ): Promise<OBISSearchResponse> {
    const params: OBISSearchParams = {
      marine: true,
      size,
    };

    // Add Brazilian coastal area if coordinates provided
    if (latitude && longitude && radius) {
      // Create a simple bounding box around the point
      const latOffset = radius / 111000; // Rough conversion: 1 degree ≈ 111km
      const lonOffset = radius / (111000 * Math.cos(latitude * Math.PI / 180));
      
      const north = latitude + latOffset;
      const south = latitude - latOffset;
      const east = longitude + lonOffset;
      const west = longitude - lonOffset;
      
      params.geometry = `POLYGON((${west} ${south}, ${east} ${south}, ${east} ${north}, ${west} ${north}, ${west} ${south}))`;
    } else {
      // Brazilian coastal waters bounding box
      params.geometry = "POLYGON((-50 -35, -30 -35, -30 5, -50 5, -50 -35))";
    }

    return this.searchOccurrences(params);
  }

  // Get threatened marine species
  async getThreatenedMarineSpecies(size: number = 100): Promise<OBISSearchResponse> {
    const params: OBISSearchParams = {
      redlist: true,
      marine: true,
      size,
    };

    return this.searchOccurrences(params);
  }

  // Get deep sea species
  async getDeepSeaSpecies(minDepth: number = 200, size: number = 100): Promise<OBISSearchResponse> {
    const params: OBISSearchParams = {
      startdepth: minDepth,
      marine: true,
      size,
    };

    return this.searchOccurrences(params);
  }

  // Health check
  async healthCheck(): Promise<{ status: "healthy" | "unhealthy"; responseTime: number }> {
    const startTime = Date.now();
    
    try {
      await this.makeRequest("/occurrence", { size: 1 });
      
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
