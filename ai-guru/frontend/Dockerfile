# Build stage: compile the CRA production bundle.
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# CRA bakes REACT_APP_* vars in at BUILD time, not runtime - pass the real
# backend URL via --build-arg at `docker build` time, e.g.:
#   docker build --build-arg REACT_APP_API_URL=https://api.example.com .
ARG REACT_APP_API_URL=http://localhost:8001
ENV REACT_APP_API_URL=$REACT_APP_API_URL
RUN npm run build

# Serve stage: static build output served by nginx (not `npm start`, which
# is a dev server not meant for production).
FROM nginx:1.27-alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
