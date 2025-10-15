/**
 * Test Setup for SIRA RAG Service
 */

import * as admin from "firebase-admin";

// Initialize Firebase Admin for testing
if (!admin.apps.length) {
  admin.initializeApp({
    projectId: "test-project",
  });
}

// Mock environment variables for testing
process.env.ENVIRONMENT = "test";
process.env.GOOGLE_CLOUD_PROJECT = "test-project";
process.env.GEMINI_API_KEY = "test-api-key";
process.env.FIRESTORE_DATABASE = "(default)";

// Global test timeout
jest.setTimeout(30000);

// Mock external services
jest.mock("@genkit-ai/googleai", () => ({
  googleAI: jest.fn(() => ({})),
}));

jest.mock("@genkit-ai/vertexai", () => ({
  vertexAI: jest.fn(() => ({})),
}));

// Clean up after tests
afterAll(async () => {
  if (admin.apps.length > 0) {
    await Promise.all(admin.apps.map(app => app?.delete()));
  }
});
