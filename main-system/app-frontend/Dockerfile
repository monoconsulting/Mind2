FROM nginx:1.25-alpine

# Copy built frontend files
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]