# Build from the repository root (the API needs ml/fs_ml and the tested models):
#   docker build -f ml-api/Dockerfile -t field-shift-ml-api .
#   docker run --rm -p 8000:8000 -e ML_API_CORS_ORIGINS=http://localhost:5173 field-shift-ml-api
FROM python:3.14-slim
WORKDIR /srv
COPY ml-api/requirements.txt ml-api/requirements.txt
RUN pip install --no-cache-dir -r ml-api/requirements.txt
COPY ml/fs_ml ml/fs_ml
COPY ml/artifacts/final_model ml/artifacts/final_model
COPY ml/artifacts/projections/projection_card.json ml/artifacts/projections/hindcast_skill_by_lead.csv ml/artifacts/projections/
COPY docs/SPROUT_PERSONA.md docs/SPROUT_PERSONA.md
COPY ml-api/app ml-api/app
COPY ml-api/data ml-api/data
WORKDIR /srv/ml-api
RUN useradd --no-create-home api
USER api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
