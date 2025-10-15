/**
 * Error Handling for SIRA RAG Service
 */

import { Request, Response, NextFunction } from "express";
import { logger } from "./logger";

// Custom error classes
export class AppError extends Error {
  public statusCode: number;
  public isOperational: boolean;
  public code?: string;

  constructor(message: string, statusCode: number, code?: string) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    this.code = code;

    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends AppError {
  constructor(message: string, field?: string) {
    super(message, 400, "VALIDATION_ERROR");
    this.name = "ValidationError";
    if (field) {
      this.message = `${field}: ${message}`;
    }
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string) {
    super(`${resource} not found`, 404, "NOT_FOUND");
    this.name = "NotFoundError";
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string = "Unauthorized") {
    super(message, 401, "UNAUTHORIZED");
    this.name = "UnauthorizedError";
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string = "Forbidden") {
    super(message, 403, "FORBIDDEN");
    this.name = "ForbiddenError";
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super(message, 409, "CONFLICT");
    this.name = "ConflictError";
  }
}

export class RateLimitError extends AppError {
  constructor(message: string = "Rate limit exceeded") {
    super(message, 429, "RATE_LIMIT_EXCEEDED");
    this.name = "RateLimitError";
  }
}

export class ExternalServiceError extends AppError {
  public service: string;

  constructor(service: string, message: string, statusCode: number = 502) {
    super(`${service}: ${message}`, statusCode, "EXTERNAL_SERVICE_ERROR");
    this.name = "ExternalServiceError";
    this.service = service;
  }
}

export class RAGError extends AppError {
  public operation: string;

  constructor(operation: string, message: string, statusCode: number = 500) {
    super(`RAG ${operation}: ${message}`, statusCode, "RAG_ERROR");
    this.name = "RAGError";
    this.operation = operation;
  }
}

export class IngestionError extends AppError {
  public source: string;

  constructor(source: string, message: string, statusCode: number = 500) {
    super(`Ingestion ${source}: ${message}`, statusCode, "INGESTION_ERROR");
    this.name = "IngestionError";
    this.source = source;
  }
}

// Error response interface
interface ErrorResponse {
  error: {
    message: string;
    code?: string;
    statusCode: number;
    timestamp: string;
    path?: string;
    details?: any;
  };
}

// Send error response
const sendErrorResponse = (
  res: Response,
  error: AppError,
  req?: Request
): void => {
  const errorResponse: ErrorResponse = {
    error: {
      message: error.message,
      code: error.code,
      statusCode: error.statusCode,
      timestamp: new Date().toISOString(),
      path: req?.path,
    },
  };

  // Add stack trace in development
  if (process.env.NODE_ENV === "development") {
    errorResponse.error.details = {
      stack: error.stack,
    };
  }

  res.status(error.statusCode).json(errorResponse);
};

// Handle operational errors
const handleOperationalError = (
  error: AppError,
  req: Request,
  res: Response
): void => {
  logger.warn("Operational error", {
    message: error.message,
    statusCode: error.statusCode,
    code: error.code,
    path: req.path,
    method: req.method,
    ip: req.ip,
    userAgent: req.get("User-Agent"),
  });

  sendErrorResponse(res, error, req);
};

// Handle programming errors
const handleProgrammingError = (
  error: Error,
  req: Request,
  res: Response
): void => {
  logger.error("Programming error", error, {
    path: req.path,
    method: req.method,
    ip: req.ip,
    userAgent: req.get("User-Agent"),
    body: req.body,
    query: req.query,
    params: req.params,
  });

  // Don't leak error details in production
  const message = process.env.NODE_ENV === "production" 
    ? "Internal server error" 
    : error.message;

  const appError = new AppError(message, 500, "INTERNAL_ERROR");
  sendErrorResponse(res, appError, req);
};

// Main error handler middleware
export const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  // If response was already sent, delegate to default Express error handler
  if (res.headersSent) {
    return next(error);
  }

  // Handle operational errors
  if (error instanceof AppError && error.isOperational) {
    handleOperationalError(error, req, res);
    return;
  }

  // Handle specific error types
  if (error.name === "ValidationError") {
    const appError = new ValidationError(error.message);
    handleOperationalError(appError, req, res);
    return;
  }

  if (error.name === "CastError") {
    const appError = new ValidationError("Invalid ID format");
    handleOperationalError(appError, req, res);
    return;
  }

  if (error.name === "MongoError" && (error as any).code === 11000) {
    const appError = new ConflictError("Duplicate field value");
    handleOperationalError(appError, req, res);
    return;
  }

  // Handle programming errors
  handleProgrammingError(error, req, res);
};

// Async error wrapper
export const asyncHandler = (
  fn: (req: Request, res: Response, next: NextFunction) => Promise<any>
) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

// Global unhandled rejection handler
export const handleUnhandledRejection = (): void => {
  process.on("unhandledRejection", (reason: any, promise: Promise<any>) => {
    logger.error("Unhandled Rejection", reason, { promise });
    // Gracefully close the server
    process.exit(1);
  });
};

// Global uncaught exception handler
export const handleUncaughtException = (): void => {
  process.on("uncaughtException", (error: Error) => {
    logger.error("Uncaught Exception", error);
    // Gracefully close the server
    process.exit(1);
  });
};
