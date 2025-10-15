/**
 * Basic health check tests for SIRA RAG Service
 */

import request from "supertest";
import express from "express";
import { healthRoutes } from "../routes/health-routes";

// Create test app
const app = express();
app.use(express.json());
app.use("/health", healthRoutes);

describe("Health Check Routes", () => {
  describe("GET /health", () => {
    it("should return basic health status", async () => {
      const response = await request(app)
        .get("/health")
        .expect(200);

      expect(response.body).toHaveProperty("status");
      expect(response.body).toHaveProperty("timestamp");
      expect(response.body).toHaveProperty("uptime");
      expect(response.body.status).toBe("healthy");
    });
  });

  describe("GET /health/ready", () => {
    it("should return readiness status", async () => {
      const response = await request(app)
        .get("/health/ready");

      expect([200, 503]).toContain(response.status);
      expect(response.body).toHaveProperty("status");
      expect(response.body).toHaveProperty("timestamp");
      expect(["healthy", "unhealthy", "not ready"]).toContain(response.body.status);
    });
  });

  describe("GET /health/live", () => {
    it("should return liveness status", async () => {
      const response = await request(app)
        .get("/health/live")
        .expect(200);

      expect(response.body).toHaveProperty("status", "alive");
      expect(response.body).toHaveProperty("timestamp");
      expect(response.body).toHaveProperty("uptime");
    });
  });

  describe("GET /health/detailed", () => {
    it("should return detailed health status", async () => {
      const response = await request(app)
        .get("/health/detailed");

      expect(response.body).toHaveProperty("status");
      expect(response.body).toHaveProperty("services");
      expect(response.body).toHaveProperty("timestamp");
      expect(response.body).toHaveProperty("uptime");
      expect(response.body).toHaveProperty("version");
      expect(response.body).toHaveProperty("environment");

      // Check services
      expect(response.body.services).toHaveProperty("firestore");
      expect(response.body.services).toHaveProperty("vertexai");
      expect(response.body.services).toHaveProperty("gemini");
      expect(response.body.services).toHaveProperty("gbif");
      expect(response.body.services).toHaveProperty("iucn");
      expect(response.body.services).toHaveProperty("obis");
      expect(response.body.services).toHaveProperty("ebird");
    });
  });
});
