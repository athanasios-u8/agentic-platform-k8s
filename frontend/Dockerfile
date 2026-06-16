FROM nginx:1.27-alpine

COPY index.html /usr/share/nginx/html/index.html
COPY src /usr/share/nginx/html/src

ENV FRONTEND_GATEWAY_PUBLIC_URL=http://localhost:8300
ENV CHATKIT_API_PATH=/chatkit

CMD sh -c 'printf "window.BOOKSTORE_CONFIG = { gatewayUrl: \"%s\", chatkitPath: \"%s\" };\n" "$FRONTEND_GATEWAY_PUBLIC_URL" "$CHATKIT_API_PATH" > /usr/share/nginx/html/config.js && nginx -g "daemon off;"'

