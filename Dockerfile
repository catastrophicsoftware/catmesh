FROM alpine
RUN apk update && apk add python3 && pip3 install hvac boto3 && mkdir /app
COPY *.py /app/

ENV CATMESH_HOSTED_ZONE_ID none
ENV CATMESH_VAULT_TOKEN none
ENV CATMESH_VAULT_ADDR none

CMD python3 /app/mesh.py