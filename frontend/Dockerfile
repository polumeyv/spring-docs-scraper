# Frontend Dockerfile for Svelte 5 + SvelteKit 2
# Development stage
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies)
RUN npm install --legacy-peer-deps

# Copy source files
COPY . .

# Expose dev server port
EXPOSE 5173

# Start dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Builder stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy source files
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

# Copy built application
COPY --from=builder /app/build build/
COPY --from=builder /app/package*.json ./

# Install production dependencies only
RUN npm ci --production --legacy-peer-deps

# Expose production port
EXPOSE 3000

# Start the application
CMD ["node", "build"]