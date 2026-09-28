# Stage 1: Build the application
FROM node:lts-alpine as build-stage

WORKDIR /app

COPY package*.json ./

RUN npm install --force --legacy-peer-deps 

COPY . .

RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:stable-alpine as production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY nginx.security-headers.conf /etc/nginx/conf.d/security-headers.conf

RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    find /usr/share/nginx/html -type f -exec chmod 644 {} \;

RUN chmod -R 755 /var/cache/nginx && \
    chmod -R 755 /var/log/nginx && \
    chmod -R 755 /etc/nginx

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]