/**
 * eBird API Client
 * https://documenter.getpostman.com/view/664302/S1ENwy59
 */

import { config } from "../config/environment";
import { logger, logDataSourceOperation } from "../utils/logger";
import { ExternalServiceError } from "../utils/error-handler";

// eBird API interfaces
export interface EBirdObservation {
  speciesCode: string;
  comName: string;
  sciName: string;
  locId: string;
  locName: string;
  obsDt: string;
  howMany?: number;
  lat: number;
  lng: number;
  obsValid: boolean;
  obsReviewed: boolean;
  locationPrivate: boolean;
  subId: string;
  subnational2Code?: string;
  subnational2Name?: string;
  subnational1Code?: string;
  subnational1Name?: string;
  countryCode: string;
  countryName: string;
  userDisplayName?: string;
  obsId?: string;
  checklistId?: string;
  presenceNoted?: boolean;
  hasComments?: boolean;
  firstName?: string;
  lastName?: string;
  hasRichMedia?: boolean;
}

export interface EBirdRegion {
  code: string;
  name: string;
}

export interface EBirdHotspot {
  locId: string;
  locName: string;
  countryCode: string;
  subnational1Code: string;
  subnational2Code?: string;
  lat: number;
  lng: number;
  latestObsDt?: string;
  numSpeciesAllTime?: number;
}

export interface EBirdSpecies {
  speciesCode: string;
  comName: string;
  sciName: string;
  category: string;
  taxonOrder: number;
  bandingCodes?: string[];
  comNameCodes?: string[];
  sciNameCodes?: string[];
  order?: string;
  familyCode?: string;
  familyComName?: string;
  familySciName?: string;
}

export interface EBirdFrequency {
  comName: string;
  monthlyFrequency: number[];
  speciesCode: string;
}

export interface EBirdSearchParams {
  regionCode?: string;
  speciesCode?: string;
  back?: number;
  maxResults?: number;
  locale?: string;
  provisional?: boolean;
  hotspot?: boolean;
  includeProvisional?: boolean;
  r?: string[];
  sppLocale?: string;
}

export class EBirdClient {
  private baseUrl: string;
  private apiKey: string;
  private timeout: number;

  constructor() {
    this.baseUrl = config.dataSources.ebird.apiUrl;
    this.apiKey = config.dataSources.ebird.apiKey;
    this.timeout = config.dataSources.ebird.timeout;

    if (!this.apiKey) {
      logger.warn("eBird API key not configured - some features may not work");
    }
  }

  private async makeRequest<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const startTime = Date.now();
    const url = new URL(endpoint, this.baseUrl);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach(v => url.searchParams.append(key, String(v)));
          } else {
            url.searchParams.append(key, String(value));
          }
        }
      });
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const headers: Record<string, string> = {
        "Accept": "application/json",
        "User-Agent": "SIRA-RAG-Service/1.0.0",
      };

      if (this.apiKey) {
        headers["X-eBirdApiToken"] = this.apiKey;
      }

      const response = await fetch(url.toString(), {
        method: "GET",
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new ExternalServiceError(
          "eBird",
          `HTTP ${response.status}: ${response.statusText}`,
          response.status
        );
      }

      const data = await response.json() as T;
      const duration = Date.now() - startTime;

      logDataSourceOperation("eBird", endpoint, "success", duration, {
        url: url.toString(),
        statusCode: response.status,
      });

      return data;

    } catch (error) {
      const duration = Date.now() - startTime;
      
      logDataSourceOperation("eBird", endpoint, "error", duration, {
        url: url.toString(),
        error: error instanceof Error ? error.message : String(error),
      });

      if (error instanceof ExternalServiceError) {
        throw error;
      }

      throw new ExternalServiceError(
        "eBird",
        `Request failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  // Get recent observations in a region
  async getRecentObservations(regionCode: string, params: EBirdSearchParams = {}): Promise<EBirdObservation[]> {
    logger.info("eBird get recent observations", { regionCode, params });
    return this.makeRequest<EBirdObservation[]>(`/data/obs/${regionCode}/recent`, params);
  }

  // Get recent notable observations in a region
  async getRecentNotableObservations(regionCode: string, params: EBirdSearchParams = {}): Promise<EBirdObservation[]> {
    logger.info("eBird get recent notable observations", { regionCode, params });
    return this.makeRequest<EBirdObservation[]>(`/data/obs/${regionCode}/recent/notable`, params);
  }

  // Get recent observations of a species in a region
  async getRecentSpeciesObservations(regionCode: string, speciesCode: string, params: EBirdSearchParams = {}): Promise<EBirdObservation[]> {
    logger.info("eBird get recent species observations", { regionCode, speciesCode, params });
    return this.makeRequest<EBirdObservation[]>(`/data/obs/${regionCode}/recent/${speciesCode}`, params);
  }

  // Get nearest observations of a species
  async getNearestSpeciesObservations(
    latitude: number,
    longitude: number,
    speciesCode: string,
    params: EBirdSearchParams = {}
  ): Promise<EBirdObservation[]> {
    logger.info("eBird get nearest species observations", { latitude, longitude, speciesCode, params });
    return this.makeRequest<EBirdObservation[]>(`/data/nearest/geo/recent/${speciesCode}`, {
      lat: latitude,
      lng: longitude,
      ...params,
    });
  }

  // Get nearby observations
  async getNearbyObservations(
    latitude: number,
    longitude: number,
    params: EBirdSearchParams = {}
  ): Promise<EBirdObservation[]> {
    logger.info("eBird get nearby observations", { latitude, longitude, params });
    return this.makeRequest<EBirdObservation[]>("/data/obs/geo/recent", {
      lat: latitude,
      lng: longitude,
      ...params,
    });
  }

  // Get nearby notable observations
  async getNearbyNotableObservations(
    latitude: number,
    longitude: number,
    params: EBirdSearchParams = {}
  ): Promise<EBirdObservation[]> {
    logger.info("eBird get nearby notable observations", { latitude, longitude, params });
    return this.makeRequest<EBirdObservation[]>("/data/obs/geo/recent/notable", {
      lat: latitude,
      lng: longitude,
      ...params,
    });
  }

  // Get species list for a region
  async getSpeciesList(regionCode: string): Promise<EBirdSpecies[]> {
    logger.info("eBird get species list", { regionCode });
    return this.makeRequest<EBirdSpecies[]>(`/ref/taxonomy/ebird`, { locale: "pt", region: regionCode });
  }

  // Get hotspots in a region
  async getHotspots(regionCode: string, params: { back?: number; fmt?: string } = {}): Promise<EBirdHotspot[]> {
    logger.info("eBird get hotspots", { regionCode, params });
    return this.makeRequest<EBirdHotspot[]>(`/ref/hotspot/${regionCode}`, params);
  }

  // Get nearby hotspots
  async getNearbyHotspots(
    latitude: number,
    longitude: number,
    params: { dist?: number; back?: number; fmt?: string } = {}
  ): Promise<EBirdHotspot[]> {
    logger.info("eBird get nearby hotspots", { latitude, longitude, params });
    return this.makeRequest<EBirdHotspot[]>("/ref/hotspot/geo", {
      lat: latitude,
      lng: longitude,
      ...params,
    });
  }

  // Get regions
  async getRegions(regionType: "country" | "subnational1" | "subnational2", parentRegion?: string): Promise<EBirdRegion[]> {
    logger.info("eBird get regions", { regionType, parentRegion });
    const endpoint = parentRegion 
      ? `/ref/region/list/${regionType}/${parentRegion}`
      : `/ref/region/list/${regionType}`;
    return this.makeRequest<EBirdRegion[]>(endpoint);
  }

  // Get Brazilian bird observations
  async getBrazilianBirdObservations(params: EBirdSearchParams = {}): Promise<EBirdObservation[]> {
    logger.info("eBird get Brazilian bird observations", { params });
    return this.getRecentObservations("BR", { maxResults: 1000, ...params });
  }

  // Get Brazilian endemic species observations
  async getBrazilianEndemicObservations(params: EBirdSearchParams = {}): Promise<EBirdObservation[]> {
    logger.info("eBird get Brazilian endemic observations", { params });
    return this.getRecentNotableObservations("BR", { maxResults: 500, ...params });
  }

  // Get Atlantic Forest bird observations
  async getAtlanticForestBirds(
    latitude: number = -23.5505,
    longitude: number = -46.6333,
    radius: number = 50,
    params: EBirdSearchParams = {}
  ): Promise<EBirdObservation[]> {
    logger.info("eBird get Atlantic Forest birds", { latitude, longitude, radius, params });
    return this.getNearbyObservations(latitude, longitude, { 
      maxResults: 500,
      back: 30, // Last 30 days
      ...params 
    });
  }

  // Health check
  async healthCheck(): Promise<{ status: "healthy" | "unhealthy"; responseTime: number; error?: string }> {
    const startTime = Date.now();
    
    try {
      if (!this.apiKey) {
        return {
          status: "unhealthy",
          responseTime: Date.now() - startTime,
          error: "API key not configured",
        };
      }

      await this.getRecentObservations("BR", { maxResults: 1 });
      
      return {
        status: "healthy",
        responseTime: Date.now() - startTime,
      };
    } catch (error) {
      return {
        status: "unhealthy",
        responseTime: Date.now() - startTime,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
}
