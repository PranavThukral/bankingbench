FROM python:3.12-slim
ENV PYTHONHASHSEED=0 TZ=UTC PYTHONDONTWRITEBYTECODE=1 HYPOTHESIS_PROFILE=ci BB_TMP=/tmp/bankingbench
WORKDIR /pack
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --no-deps -r /tmp/requirements.lock
CMD ["sleep", "infinity"]
