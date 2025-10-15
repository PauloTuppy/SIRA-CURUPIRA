/**
 * Ingestion Routes for SIRA RAG Service
 * Placeholder implementation - will be expanded in next subtasks
 */

import { Router, Request, Response } from "express";
import { logger } from "../utils/logger";
import { asyncHandler } from "../utils/error-handler";
import { IngestionService, IngestionJobConfig } from "../services/ingestion-service";

const router = Router();
const ingestionService = new IngestionService();

// Ingestion job interface
interface IngestionJobRequest {
  source: "gbif" | "iucn" | "obis" | "ebird";
  parameters?: {
    species?: string;
    location?: string;
    dateRange?: {
      start: string;
      end: string;
    };
    limit?: number;
  };
}

interface IngestionJobResponse {
  jobId: string;
  source: string;
  status: "queued" | "running" | "completed" | "failed";
  parameters: any;
  createdAt: string;
  estimatedDuration?: number;
}

// Start ingestion job
router.post("/start", asyncHandler(async (req: Request, res: Response): Promise<void> => {
  const { source, parameters }: IngestionJobRequest = req.body;

  // Validate request
  if (!source || !["gbif", "iucn", "obis", "ebird"].includes(source)) {
    res.status(400).json({
      error: "Source is required and must be one of: gbif, iucn, obis, ebird",
    });
    return;
  }

  logger.info("Ingestion job requested", {
    source,
    parameters,
  });

  // Create ingestion job configuration
  const jobConfig: IngestionJobConfig = {
    source,
    parameters: {
      species: parameters?.species,
      location: parameters?.location ? {
        country: typeof parameters.location === 'string' ? parameters.location : undefined,
      } : undefined,
      dateRange: parameters?.dateRange,
      limit: parameters?.limit,
    },
    options: {
      generateEmbeddings: true,
      batchSize: 10,
    },
  };

  // Start ingestion job
  const jobId = await ingestionService.startIngestionJob(jobConfig);

  const response: IngestionJobResponse = {
    jobId,
    source,
    status: "queued",
    parameters: parameters || {},
    createdAt: new Date().toISOString(),
    estimatedDuration: 300000, // 5 minutes estimate
  };

  res.status(202).json(response);
}));

// Get ingestion job status
router.get("/job/:jobId", asyncHandler(async (req: Request, res: Response) => {
  const { jobId } = req.params;

  logger.info("Ingestion job status requested", { jobId });

  // Get job status from service
  const jobStatus = await ingestionService.getJobStatus(jobId);

  if (!jobStatus) {
    res.status(404).json({
      error: "Job not found",
      jobId,
    });
    return;
  }

  // Convert Firestore timestamps to ISO strings for response
  const response = {
    ...jobStatus,
    createdAt: jobStatus.createdAt.toDate().toISOString(),
    startedAt: jobStatus.startedAt?.toDate().toISOString(),
    completedAt: jobStatus.completedAt?.toDate().toISOString(),
    duration: jobStatus.completedAt && jobStatus.startedAt
      ? jobStatus.completedAt.toMillis() - jobStatus.startedAt.toMillis()
      : undefined,
  };

  res.json(response);
}));

// List ingestion jobs
router.get("/jobs", asyncHandler(async (req: Request, res: Response) => {
  const { source, status, limit = 10, offset = 0 } = req.query;

  logger.info("Ingestion jobs list requested", {
    source,
    status,
    limit,
    offset,
  });

  // Get jobs from service
  const { jobs, total } = await ingestionService.listJobs({
    source: source as string,
    status: status as string,
    limit: parseInt(limit as string, 10),
    offset: parseInt(offset as string, 10),
  });

  // Convert Firestore timestamps to ISO strings for response
  const formattedJobs = jobs.map(job => ({
    ...job,
    createdAt: job.createdAt.toDate().toISOString(),
    startedAt: job.startedAt?.toDate().toISOString(),
    completedAt: job.completedAt?.toDate().toISOString(),
    duration: job.completedAt && job.startedAt
      ? job.completedAt.toMillis() - job.startedAt.toMillis()
      : undefined,
  }));

  const response = {
    jobs: formattedJobs,
    total,
    limit: parseInt(limit as string, 10),
    offset: parseInt(offset as string, 10),
  };

  res.json(response);
}));

// Cancel ingestion job
router.delete("/job/:jobId", asyncHandler(async (req: Request, res: Response) => {
  const { jobId } = req.params;

  logger.info("Ingestion job cancellation requested", { jobId });

  // Cancel job using service
  await ingestionService.cancelJob(jobId);

  const response = {
    jobId,
    status: "cancelled",
    message: "Job cancellation requested",
    timestamp: new Date().toISOString(),
  };

  res.json(response);
}));

// Get ingestion statistics
router.get("/stats", asyncHandler(async (req: Request, res: Response) => {
  logger.info("Ingestion stats requested");

  // Get basic job statistics
  const { jobs: allJobs } = await ingestionService.listJobs({ limit: 1000 });

  const totalJobs = allJobs.length;
  const activeJobs = allJobs.filter(job => job.status === "running" || job.status === "queued").length;
  const completedJobs = allJobs.filter(job => job.status === "completed").length;
  const failedJobs = allJobs.filter(job => job.status === "failed").length;

  // Calculate totals from completed jobs
  const completedJobsWithResults = allJobs.filter(job => job.status === "completed" && job.results);
  const totalDocumentsIngested = completedJobsWithResults.reduce((sum, job) =>
    sum + (job.results?.documentsIngested || 0), 0);
  const totalEmbeddingsCreated = completedJobsWithResults.reduce((sum, job) =>
    sum + (job.results?.embeddingsCreated || 0), 0);

  // Source breakdown
  const sourceStats = {
    gbif: {
      jobs: allJobs.filter(job => job.source === "gbif").length,
      documents: completedJobsWithResults
        .filter(job => job.source === "gbif")
        .reduce((sum, job) => sum + (job.results?.documentsIngested || 0), 0)
    },
    iucn: {
      jobs: allJobs.filter(job => job.source === "iucn").length,
      documents: completedJobsWithResults
        .filter(job => job.source === "iucn")
        .reduce((sum, job) => sum + (job.results?.documentsIngested || 0), 0)
    },
    obis: {
      jobs: allJobs.filter(job => job.source === "obis").length,
      documents: completedJobsWithResults
        .filter(job => job.source === "obis")
        .reduce((sum, job) => sum + (job.results?.documentsIngested || 0), 0)
    },
    ebird: {
      jobs: allJobs.filter(job => job.source === "ebird").length,
      documents: completedJobsWithResults
        .filter(job => job.source === "ebird")
        .reduce((sum, job) => sum + (job.results?.documentsIngested || 0), 0)
    },
  };

  // Find last ingestion
  const lastCompletedJob = completedJobsWithResults
    .sort((a, b) => (b.completedAt?.toMillis() || 0) - (a.completedAt?.toMillis() || 0))[0];

  const response = {
    totalJobs,
    activeJobs,
    completedJobs,
    failedJobs,
    totalDocumentsIngested,
    totalEmbeddingsCreated,
    sourceStats,
    lastIngestion: lastCompletedJob ? {
      jobId: lastCompletedJob.jobId,
      source: lastCompletedJob.source,
      completedAt: lastCompletedJob.completedAt?.toDate().toISOString(),
      documentsIngested: lastCompletedJob.results?.documentsIngested || 0,
    } : null,
  };

  res.json(response);
}));

export { router as ingestionRoutes };
