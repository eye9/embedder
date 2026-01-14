# Cleanup script for Windows containers
Write-Host "Cleaning up Windows containers and networks..." -ForegroundColor Yellow

# Stop and remove all containers
docker stop $(docker ps -aq) 2>$null
docker rm $(docker ps -aq) 2>$null

# Remove networks
docker network rm embedder_batch_processor_network 2>$null
docker network rm batch_processor_network 2>$null

# Remove unused networks
docker network prune -f

# List current networks
Write-Host "Current Docker networks:" -ForegroundColor Green
docker network ls

Write-Host "Cleanup completed!" -ForegroundColor Green