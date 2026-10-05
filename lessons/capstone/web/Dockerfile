FROM node:22-alpine
WORKDIR /web
# .npmrc points npm at the approved Microsoft feed (public npm is blocked on this laptop).
COPY package.json package-lock.json .npmrc ./
RUN npm ci --no-audit --no-fund
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]
