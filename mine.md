# 1. Build images and start all containers
make build
make up
# 2. Run database migrations (creates all tables + seeds otomoto source)
make migrate

make api-logs
make worker-logs

dccker compose restart api
docker compose up -d --force-recreate beat
docker compose build worker && docker compose up -d --force-recreate worker

# 3. Create your user
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "mikolaj.borecki1@gmail.com"}'

# 4. Create a filter (save the user id from step 3)
curl -X POST http://localhost:8000/users/675433eb-b630-4d4f-a98a-919a0163985d/filters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My first filter",
    "brand": "Toyota",
    "price_max": 100000,
    "year_min": 2018,
    "fuel_types": ["hybrid", "petrol"]
  }'

# 5. Trigger a manual scrape to test
curl -X POST http://localhost:8000/admin/scrape/trigger \
  -H "X-Admin-Key: change-me-in-production"

http://localhost:8000/listings
