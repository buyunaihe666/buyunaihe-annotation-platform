FROM docker.1ms.run/library/node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm config set registry https://registry.npmmirror.com && npm ci
COPY . .
# Skip vue-tsc type check to save memory on low-RAM servers
RUN npx vite build

FROM docker.1ms.run/library/nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]