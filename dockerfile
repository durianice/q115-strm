FROM python:3.12-slim
EXPOSE 11566
WORKDIR /root

ENV PATH=/root:$PATH
ENV TZ="Asia/Shanghai"

# RUN cp /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list.d/debian.sources.bak \
#   && sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources
RUN apt update && apt install -y git cron curl

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

COPY . .

RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

VOLUME ["/root/data"]

ENTRYPOINT ["python", "app/main.py"]
