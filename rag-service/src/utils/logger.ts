/**
 * Structured Logging for SIRA RAG Service
 */

import winston from "winston";
import { config } from "../config/environment";

// Define log levels
const levels = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4,
};

// Define colors for each level
const colors = {
  error: "red",
  warn: "yellow",
  info: "green",
  http: "magenta",
  debug: "white",
};

// Tell winston that you want to link the colors
winston.addColors(colors);

// Define format for logs
const format = winston.format.combine(
  winston.format.timestamp({ format: "YYYY-MM-DD HH:mm:ss:ms" }),
  winston.format.errors({ stack: true }),
  winston.format.colorize({ all: true }),
  winston.format.printf((info) => {
    const { timestamp, level, message, ...meta } = info;
    
    let logMessage = `${timestamp} [${level}]: ${message}`;
    
    // Add metadata if present
    if (Object.keys(meta).length > 0) {
      logMessage += ` ${JSON.stringify(meta, null, 2)}`;
    }
    
    return logMessage;
  })
);

// Define format for production (JSON)
const productionFormat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json()
);

// Define which transports the logger must use
const transports = [
  // Console transport
  new winston.transports.Console({
    format: config.app.environment === "production" ? productionFormat : format,
  }),
];

// Add file transport for production
if (config.app.environment === "production") {
  transports.push(
    new winston.transports.File({
      filename: "logs/error.log",
      level: "error",
      format: productionFormat,
    }) as any,
    new winston.transports.File({
      filename: "logs/combined.log",
      format: productionFormat,
    }) as any
  );
}

// Create the logger
export const logger = winston.createLogger({
  level: config.app.debug ? "debug" : "info",
  levels,
  format: config.app.environment === "production" ? productionFormat : format,
  transports,
  exitOnError: false,
});

// Create a stream object for Morgan HTTP logging
export const loggerStream = {
  write: (message: string): void => {
    logger.http(message.trim());
  },
};

// Helper functions for structured logging
export const logInfo = (message: string, meta?: any): void => {
  logger.info(message, meta);
};

export const logError = (message: string, error?: Error | any, meta?: any): void => {
  logger.error(message, {
    error: error?.message || error,
    stack: error?.stack,
    ...meta,
  });
};

export const logWarn = (message: string, meta?: any): void => {
  logger.warn(message, meta);
};

export const logDebug = (message: string, meta?: any): void => {
  logger.debug(message, meta);
};

// Performance logging
export const logPerformance = (operation: string, duration: number, meta?: any): void => {
  logger.info(`Performance: ${operation}`, {
    duration: `${duration}ms`,
    ...meta,
  });
};

// RAG-specific logging
export const logRAGOperation = (
  operation: string,
  query: string,
  results: number,
  duration: number,
  meta?: any
): void => {
  logger.info(`RAG ${operation}`, {
    query: query.substring(0, 100) + (query.length > 100 ? "..." : ""),
    resultsCount: results,
    duration: `${duration}ms`,
    ...meta,
  });
};

// Data source logging
export const logDataSourceOperation = (
  source: string,
  operation: string,
  status: "success" | "error",
  duration: number,
  meta?: any
): void => {
  logger.info(`DataSource ${source} ${operation}`, {
    status,
    duration: `${duration}ms`,
    ...meta,
  });
};

// Ingestion logging
export const logIngestion = (
  source: string,
  documentsProcessed: number,
  duration: number,
  meta?: any
): void => {
  logger.info(`Ingestion ${source}`, {
    documentsProcessed,
    duration: `${duration}ms`,
    ...meta,
  });
};
