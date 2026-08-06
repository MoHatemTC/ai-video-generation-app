# frontend/Dockerfile
FROM node:20-slim

WORKDIR /app

# Install deps first (better layer caching -> faster rebuilds)
COPY package*.json ./
RUN npm install

# Now copy the actual code
COPY . .

EXPOSE 5173

# --host is required so Vite listens on all interfaces inside the container,
# not just localhost (otherwise it's unreachable from outside the container)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
