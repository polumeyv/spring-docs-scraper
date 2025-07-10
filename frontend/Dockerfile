# Frontend Dockerfile for Svelte 5 + SvelteKit 2
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy built application
COPY --from=builder /app/build build/
COPY --from=builder /app/package*.json ./

# Install production dependencies
RUN npm ci --production

# Expose port
EXPOSE 3000

# Start the application
CMD ["node", "build"]