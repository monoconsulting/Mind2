# Stage 1: Build the React application
FROM node:18-alpine AS builder
WORKDIR /app

# Copy application manifest and lock file
COPY main-system/app-frontend/package.json main-system/app-frontend/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY main-system/app-frontend .

# Copy the shared status definitions to root (needed by Process.jsx import path)
COPY shared /shared

# Accept build argument and set as environment variable for Vite
ARG VITE_REFRESH_INTERVAL_SECONDS=10
ENV VITE_REFRESH_INTERVAL_SECONDS=${VITE_REFRESH_INTERVAL_SECONDS}

# Build the application
RUN npm run build

# Stage 2: Serve the application using Nginx
FROM nginx:1.25-alpine

# Copy the custom Nginx configuration
COPY main-system/app-frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built static files from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
