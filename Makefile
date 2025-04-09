
.PHONY: back

back:
	set TARGET=dev&& uvicorn back.main:app --reload

back_install:
	poetry install


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

gen_migration:
	set TARGET=dev&& alembic revision --autogenerate -m "first migration"

migration:
	alembic upgrade head

down_migration:
	alembic downgrade -1