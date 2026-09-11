FROM node:20-alpine AS build
WORKDIR /app

# npm 源可通过构建参数覆盖（国内服务器建议用镜像源）
ARG NPM_REGISTRY=https://registry.npmjs.org

COPY package.json ./
RUN npm config set registry ${NPM_REGISTRY} \
 && npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
