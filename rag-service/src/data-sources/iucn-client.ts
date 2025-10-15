/**
 * IUCN Red List API Client
 * https://apiv3.iucnredlist.org/api/v3/docs
 */

import { config } from "../config/environment";
import { logger, logDataSourceOperation } from "../utils/logger";
import { ExternalServiceError } from "../utils/error-handler";

// IUCN API interfaces
export interface IUCNSpecies {
  taxonid: number;
  scientific_name: string;
  kingdom: string;
  phylum: string;
  class: string;
  order: string;
  family: string;
  genus: string;
  main_common_name?: string;
  authority?: string;
  published_year?: number;
  assessment_date?: string;
  category: string;
  criteria?: string;
  population_trend?: string;
  marine_system?: boolean;
  freshwater_system?: boolean;
  terrestrial_system?: boolean;
  assessor?: string;
  reviewer?: string;
  aoo_km2?: string;
  eoo_km2?: string;
  elevation_upper?: number;
  elevation_lower?: number;
  depth_upper?: number;
  depth_lower?: number;
  errata_flag?: boolean;
  errata_reason?: string;
  amended_flag?: boolean;
  amended_reason?: string;
}

export interface IUCNAssessment {
  taxonid: number;
  scientific_name: string;
  subspecies?: string;
  rank?: string;
  subpopulation?: string;
  category: string;
  main_common_name?: string;
  authority?: string;
  published_year?: number;
  assessment_date?: string;
  criteria?: string;
  population_trend?: string;
  marine_system?: boolean;
  freshwater_system?: boolean;
  terrestrial_system?: boolean;
  assessor?: string;
  reviewer?: string;
  aoo_km2?: string;
  eoo_km2?: string;
  elevation_upper?: number;
  elevation_lower?: number;
  depth_upper?: number;
  depth_lower?: number;
  errata_flag?: boolean;
  errata_reason?: string;
  amended_flag?: boolean;
  amended_reason?: string;
}

export interface IUCNCountry {
  country: string;
  code: string;
}

export interface IUCNRegion {
  name: string;
  identifier: string;
}

export interface IUCNHabitat {
  code: string;
  habitat: string;
  suitability?: string;
  season?: string;
  majorimportance?: string;
}

export interface IUCNThreat {
  code: string;
  title: string;
  timing?: string;
  scope?: string;
  severity?: string;
  score?: string;
  invasive?: string;
}

export interface IUCNSearchResponse<T> {
  name?: string;
  result: T[];
  count?: number;
}

export interface IUCNResponse<T> {
  name?: string;
  result: T;
}

export class IUCNClient {
  private baseUrl: string;
  private apiToken: string;
  private timeout: number;

  constructor() {
    this.baseUrl = config.dataSources.iucn.apiUrl;
    this.apiToken = config.dataSources.iucn.apiToken;
    this.timeout = config.dataSources.iucn.timeout;

    if (!this.apiToken) {
      logger.warn("IUCN API token not configured - some features may not work");
    }
  }

  private async makeRequest<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const startTime = Date.now();
    const url = new URL(endpoint, this.baseUrl);
    
    // Add API token to URL
    if (this.apiToken) {
      url.searchParams.append("token", this.apiToken);
    }

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
          "IUCN",
          `HTTP ${response.status}: ${response.statusText}`,
          response.status
        );
      }

      const data = await response.json() as T;
      const duration = Date.now() - startTime;

      logDataSourceOperation("IUCN", endpoint, "success", duration, {
        url: url.toString().replace(this.apiToken || "", "***"),
        statusCode: response.status,
      });

      return data;

    } catch (error) {
      const duration = Date.now() - startTime;
      
      logDataSourceOperation("IUCN", endpoint, "error", duration, {
        url: url.toString().replace(this.apiToken || "", "***"),
        error: error instanceof Error ? error.message : String(error),
      });

      if (error instanceof ExternalServiceError) {
        throw error;
      }

      throw new ExternalServiceError(
        "IUCN",
        `Request failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  // Get species by name
  async getSpeciesByName(name: string): Promise<IUCNSearchResponse<IUCNSpecies>> {
    logger.info("IUCN get species by name", { name });
    return this.makeRequest<IUCNSearchResponse<IUCNSpecies>>(`/species/${encodeURIComponent(name)}`);
  }

  // Get species assessment
  async getSpeciesAssessment(name: string, region?: string): Promise<IUCNResponse<IUCNAssessment[]>> {
    logger.info("IUCN get species assessment", { name, region });
    const endpoint = region 
      ? `/species/${encodeURIComponent(name)}/region/${region}`
      : `/species/${encodeURIComponent(name)}`;
    return this.makeRequest<IUCNResponse<IUCNAssessment[]>>(endpoint);
  }

  // Get species by category
  async getSpeciesByCategory(category: string): Promise<IUCNSearchResponse<IUCNSpecies>> {
    logger.info("IUCN get species by category", { category });
    return this.makeRequest<IUCNSearchResponse<IUCNSpecies>>(`/species/category/${category}`);
  }

  // Get countries list
  async getCountries(): Promise<IUCNSearchResponse<IUCNCountry>> {
    logger.info("IUCN get countries");
    return this.makeRequest<IUCNSearchResponse<IUCNCountry>>("/country/list");
  }

  // Get species by country
  async getSpeciesByCountry(country: string): Promise<IUCNSearchResponse<IUCNSpecies>> {
    logger.info("IUCN get species by country", { country });
    return this.makeRequest<IUCNSearchResponse<IUCNSpecies>>(`/country/getspecies/${country}`);
  }

  // Get species habitats
  async getSpeciesHabitats(name: string): Promise<IUCNResponse<IUCNHabitat[]>> {
    logger.info("IUCN get species habitats", { name });
    return this.makeRequest<IUCNResponse<IUCNHabitat[]>>(`/species/${encodeURIComponent(name)}/habitats`);
  }

  // Get species threats
  async getSpeciesThreats(name: string): Promise<IUCNResponse<IUCNThreat[]>> {
    logger.info("IUCN get species threats", { name });
    return this.makeRequest<IUCNResponse<IUCNThreat[]>>(`/species/${encodeURIComponent(name)}/threats`);
  }

  // Get Brazilian threatened species
  async getBrazilianThreatenedSpecies(): Promise<IUCNSearchResponse<IUCNSpecies>> {
    logger.info("IUCN get Brazilian threatened species");
    return this.getSpeciesByCountry("BR");
  }

  // Get critically endangered species
  async getCriticallyEndangeredSpecies(): Promise<IUCNSearchResponse<IUCNSpecies>> {
    logger.info("IUCN get critically endangered species");
    return this.getSpeciesByCategory("CR");
  }

  // Get endangered species
  async getEndangeredSpecies(): Promise<IUCNSearchResponse<IUCNSpecies>> {
    logger.info("IUCN get endangered species");
    return this.getSpeciesByCategory("EN");
  }

  // Get vulnerable species
  async getVulnerableSpecies(): Promise<IUCNSearchResponse<IUCNSpecies>> {
    logger.info("IUCN get vulnerable species");
    return this.getSpeciesByCategory("VU");
  }

  // Health check
  async healthCheck(): Promise<{ status: "healthy" | "unhealthy"; responseTime: number; error?: string }> {
    const startTime = Date.now();
    
    try {
      if (!this.apiToken) {
        return {
          status: "unhealthy",
          responseTime: Date.now() - startTime,
          error: "API token not configured",
        };
      }

      await this.getCountries();
      
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
