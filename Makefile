
.PHONY: back

back:
	set TARGET=dev&& uvicorn back.main:app --reload

back_install:
	uv sync

redis:
	docker start Redis

postgres:
	docker start PostgreSQL

create_postgres:
	docker run --name PostgreSQL -p 5432:5432 -e POSTGRES_PASSWORD=1234 -d postgres

create_redis:
	docker run --name Redis -p 6379:6379 -d redis

create_rabbit:
	docker run -d --hostname my-rabbit --name RabbitMQ -p 5672:5672 rabbitmq:3

rabbit:
	docker start RabbitMQ

create_minio:
	docker run -d \
	--name Minio \
	-p 9000:9000 \
	-p 9001:9001 \
	-e "MINIO_ROOT_USER=minioadmin" \
	-e "MINIO_ROOT_PASSWORD=minioadmin" \
	-v /mnt/data:/data \
	quay.io/minio/minio server /data --console-address ":9001"
	
minio:
	docker start Minio

gen_migration:
	set TARGET=dev&& alembic revision --autogenerate -m "first migration"

migration:
	alembic upgrade head

down_migration:
	alembic downgrade -1

delete_migrations:
	del database\migrations\versions\*

add_db:
	uv add git+https://github.com/w1vern/deva_p1_db

delete_db:
	uv remove deva_p1_db

update_db:
	uv add -U deva_p1_db