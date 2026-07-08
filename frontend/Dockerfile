FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG API_URL=http://api:8001
ENV API_URL=$API_URL

RUN npm run build

EXPOSE 3001

CMD ["npm", "start"]
