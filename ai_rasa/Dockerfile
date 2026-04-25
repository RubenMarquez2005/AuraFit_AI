FROM rasa/rasa:3.6.20-full

WORKDIR /app

COPY . /app
USER root
RUN chmod +x /app/start-rasa.sh && chown -R 1001:0 /app
USER 1001

EXPOSE 5005

ENTRYPOINT ["/app/start-rasa.sh"]
