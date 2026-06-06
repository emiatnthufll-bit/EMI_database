FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* yarn.lock* ./
RUN npm install --silent || yarn --silent
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
